"""VajraX Station Simulator — FastAPI application entry point.

This service simulates sensor data for a single Antarctic research station.
It is parameterized entirely by the STATION_ID environment variable.

Endpoints:
  GET  /sim/status                  Current simulator state snapshot
  POST /sim/inject/{anomaly_type}   Inject a named anomaly
  DELETE /sim/inject/{anomaly_type} Clear a named anomaly
  DELETE /sim/inject                Clear ALL active anomalies
  GET  /sim/anomalies               List available anomaly types
  GET  /health                      Health check

Usage:
  STATION_ID=maitri uvicorn simulator.station_sim.main:app --port 8200
  STATION_ID=bharati uvicorn simulator.station_sim.main:app --port 8201
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import structlog
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from shared.schemas.config import StationConfig, StationId
from shared.utils.logging import configure_logging
from simulator.station_sim.generator import SensorDataGenerator, make_batch
from simulator.station_sim.publisher import SensorPublisher
from simulator.station_sim.state import AnomalyType, StationState

configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "json") == "json",
)
log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Global state (one instance per process — one process per station)
# ---------------------------------------------------------------------------

_state: StationState | None = None
_generator: SensorDataGenerator | None = None
_publisher: SensorPublisher | None = None
_config: StationConfig | None = None
_generation_task: asyncio.Task | None = None

TICK_INTERVAL_S = float(os.getenv("SIM_TICK_INTERVAL_S", "1.0"))  # physics step
FLUSH_INTERVAL_S = float(os.getenv("SIM_FLUSH_INTERVAL_S", "10.0"))  # publish batch
CONFIG_PATH_TEMPLATE = os.getenv("CONFIG_PATH_TEMPLATE", "edge/config/{station_id}.yaml")


# ---------------------------------------------------------------------------
# Background generation loop
# ---------------------------------------------------------------------------

async def _generation_loop() -> None:
    """Background task: advance state, generate readings, flush periodically."""
    global _state, _generator, _publisher
    flush_counter = 0.0

    while True:
        await asyncio.sleep(TICK_INTERVAL_S)
        await _state.step(TICK_INTERVAL_S)

        # Generate readings for all sensors
        readings = _generator.generate_all()
        _publisher.add_readings(readings)

        flush_counter += TICK_INTERVAL_S
        if flush_counter >= FLUSH_INTERVAL_S:
            await _publisher.flush()
            flush_counter = 0.0
            log.debug(
                "sim.tick",
                station_id=_state.station_id,
                tick=_state.tick,
                active_anomalies=list(_state.active_anomalies.keys()),
            )


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _state, _generator, _publisher, _config, _generation_task

    station_id = os.getenv("STATION_ID", "").strip().lower()
    if station_id not in ("maitri", "bharati"):
        raise RuntimeError(
            f"STATION_ID must be 'maitri' or 'bharati', got: {station_id!r}"
        )

    config_path = CONFIG_PATH_TEMPLATE.format(station_id=station_id)
    log.info("sim.startup", station_id=station_id, config_path=config_path)

    _config = StationConfig.from_yaml(config_path)
    _state = StationState.for_station(station_id)
    _generator = SensorDataGenerator(_config, _state)
    _publisher = SensorPublisher(
        station_id=station_id,
        batch_window_s=FLUSH_INTERVAL_S,
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
    )
    await _publisher.start()
    _generation_task = asyncio.create_task(_generation_loop())
    log.info("sim.ready", station_id=station_id, sensors=len(_config.sensors))

    yield  # app runs

    log.info("sim.shutdown", station_id=station_id)
    if _generation_task:
        _generation_task.cancel()
        try:
            await _generation_task
        except asyncio.CancelledError:
            pass
    await _publisher.stop()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VajraX Station Simulator",
    description="Simulates sensor telemetry for an Antarctic research station.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "station_id": _state.station_id if _state else None,
        "tick": _state.tick if _state else 0,
        "active_anomalies": list(_state.active_anomalies.keys()) if _state else [],
    }


@app.get("/sim/status")
async def sim_status() -> Dict[str, Any]:
    """Return a full snapshot of current simulator state."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    async with _state._lock:
        snapshot = _state.snapshot()
    snapshot["publisher"] = _publisher.stats
    snapshot["config"] = {
        "station_id": _config.station_id.value,
        "sensor_count": len(_config.sensors),
        "threshold_rule_count": len(_config.threshold_rules),
    }
    return snapshot


@app.get("/sim/anomalies")
async def list_anomaly_types() -> Dict[str, Any]:
    """List all available anomaly types and their current state."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return {
        "available": [a.value for a in AnomalyType],
        "active": list(_state.active_anomalies.keys()),
    }


@app.post("/sim/inject/{anomaly_type}")
async def inject_anomaly(
    anomaly_type: str = Path(..., description="Anomaly type name"),
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Activate a named anomaly on this station."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    try:
        anomaly = AnomalyType(anomaly_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown anomaly type: {anomaly_type!r}. "
                   f"Available: {[a.value for a in AnomalyType]}",
        )
    async with _state._lock:
        _state.inject_anomaly(anomaly, meta or {})
    log.info("sim.anomaly.injected", station_id=_state.station_id, anomaly=anomaly_type)
    return {
        "injected": anomaly_type,
        "station_id": _state.station_id,
        "active_anomalies": list(_state.active_anomalies.keys()),
    }


@app.delete("/sim/inject/{anomaly_type}")
async def clear_anomaly(
    anomaly_type: str = Path(..., description="Anomaly type name to clear"),
) -> Dict[str, Any]:
    """Deactivate a specific anomaly."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    try:
        anomaly = AnomalyType(anomaly_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown anomaly type: {anomaly_type!r}")
    async with _state._lock:
        cleared = _state.clear_anomaly(anomaly)
    log.info("sim.anomaly.cleared", station_id=_state.station_id, anomaly=anomaly_type)
    return {
        "cleared": anomaly_type,
        "was_active": cleared,
        "active_anomalies": list(_state.active_anomalies.keys()),
    }


@app.delete("/sim/inject")
async def clear_all_anomalies() -> Dict[str, Any]:
    """Deactivate all active anomalies and restore normal operations."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    async with _state._lock:
        _state.clear_all_anomalies()
    log.info("sim.anomaly.all_cleared", station_id=_state.station_id)
    return {
        "cleared": "all",
        "station_id": _state.station_id,
        "active_anomalies": [],
    }


@app.post("/sim/readings/now")
async def readings_now() -> Dict[str, Any]:
    """Force-generate and return current readings (without publishing)."""
    if _generator is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    readings = _generator.generate_all()
    return make_batch(_state.station_id, readings)
