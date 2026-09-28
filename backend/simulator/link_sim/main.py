"""VajraX Link Simulator — FastAPI control API.

Provides a clean HTTP interface for injecting and clearing satellite link
conditions during development and testing. Wraps the toxiproxy REST API.

Two link proxies are managed, one per station:
  - maitri-mqtt   listens on :18883, proxies to mosquitto-cloud:8883
  - bharati-mqtt  listens on :18884, proxies to mosquitto-cloud:8883

Edge sync agents connect to their respective toxiproxy port rather than
directly to the Cloud MQTT broker, so all traffic passes through the shim.

Endpoints:
  GET  /link/status                      Current link state for all proxies
  POST /link/outage                      Drop the link for a station
  POST /link/restore                     Restore the link for a station
  POST /link/degrade                     Apply latency + bandwidth limits
  POST /link/reset                       Remove all toxics from a station's link
  GET  /health                           Health check

Usage:
  uvicorn simulator.link_sim.main:app --port 8300
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from shared.utils.logging import configure_logging
from simulator.link_sim.toxiproxy_client import ToxiproxyClient

configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "json") == "json",
)
log = structlog.get_logger(__name__)

# Station → toxiproxy listen port
STATION_PORTS: Dict[str, int] = {
    "maitri": int(os.getenv("MAITRI_PROXY_PORT", "18883")),
    "bharati": int(os.getenv("BHARATI_PROXY_PORT", "18884")),
}
MQTT_UPSTREAM = os.getenv("MQTT_UPSTREAM", "mosquitto-cloud:8883")

_client: ToxiproxyClient | None = None

# Active outage tasks (for timed outages)
_outage_tasks: Dict[str, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = ToxiproxyClient()
    reachable = await _client.health_check()
    if reachable:
        log.info("link_sim.toxiproxy_connected")
        await _bootstrap_proxies()
    else:
        log.warning(
            "link_sim.toxiproxy_not_reachable",
            note="Link simulation endpoints will fail until toxiproxy is running.",
        )
    yield
    for task in _outage_tasks.values():
        task.cancel()
    await _client.close()


async def _bootstrap_proxies() -> None:
    """Ensure both station proxies exist in toxiproxy."""
    existing = await _client.list_proxies()
    for station_id, port in STATION_PORTS.items():
        proxy_name = f"{station_id}-mqtt"
        if proxy_name not in existing:
            await _client.create_proxy(
                name=proxy_name,
                listen=f"0.0.0.0:{port}",
                upstream=MQTT_UPSTREAM,
                enabled=True,
            )
            # Apply default satellite link characteristics
            await _client.add_latency_toxic(proxy_name, latency_ms=800, jitter_ms=200)
            log.info("link_sim.proxy_bootstrapped",
                     station_id=station_id, proxy=proxy_name, port=port)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VajraX Link Simulator",
    description="Controls satellite link simulation (via toxiproxy) for dev and testing.",
    version="1.0.0",
    lifespan=lifespan,
)


class OutageRequest(BaseModel):
    station_id: Literal["maitri", "bharati", "all"]
    duration_seconds: Optional[float] = None  # None = indefinite until /restore


class DegradeRequest(BaseModel):
    station_id: Literal["maitri", "bharati", "all"]
    latency_ms: int = 1200
    jitter_ms: int = 400
    bandwidth_kbps: int = 256
    packet_loss_pct: float = 0.0  # 0–100


class RestoreRequest(BaseModel):
    station_id: Literal["maitri", "bharati", "all"]


def _require_client():
    if _client is None:
        raise HTTPException(status_code=503, detail="Link simulator not ready")


def _stations_from(station_id: str) -> List[str]:
    if station_id == "all":
        return list(STATION_PORTS.keys())
    return [station_id]


@app.get("/health")
async def health() -> Dict[str, Any]:
    reachable = await _client.health_check() if _client else False
    return {"status": "ok", "toxiproxy_reachable": reachable}


@app.get("/link/status")
async def link_status() -> Dict[str, Any]:
    """Return current toxiproxy status for all station links."""
    _require_client()
    try:
        proxies = await _client.list_proxies()
        result = {}
        for station_id in STATION_PORTS:
            proxy_name = f"{station_id}-mqtt"
            if proxy_name in proxies:
                proxy = proxies[proxy_name]
                toxics = await _client.list_toxics(proxy_name)
                result[station_id] = {
                    "proxy": proxy_name,
                    "enabled": proxy.get("enabled", False),
                    "toxics": [t["name"] for t in toxics],
                    "outage_active": station_id in _outage_tasks and not _outage_tasks[station_id].done(),
                }
            else:
                result[station_id] = {"proxy": proxy_name, "status": "not_configured"}
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Toxiproxy error: {exc}")


@app.post("/link/outage")
async def inject_outage(req: OutageRequest) -> Dict[str, Any]:
    """Disable the satellite link for one or both stations."""
    _require_client()
    stations = _stations_from(req.station_id)
    for station_id in stations:
        proxy_name = f"{station_id}-mqtt"
        await _client.disable_proxy(proxy_name)
        # Schedule auto-restore if duration given
        if req.duration_seconds is not None:
            existing = _outage_tasks.get(station_id)
            if existing and not existing.done():
                existing.cancel()
            task = asyncio.create_task(
                _auto_restore(station_id, req.duration_seconds)
            )
            _outage_tasks[station_id] = task
    log.info("link_sim.outage_injected",
             stations=stations, duration_s=req.duration_seconds)
    return {
        "outage_injected": stations,
        "duration_seconds": req.duration_seconds,
        "auto_restore": req.duration_seconds is not None,
    }


async def _auto_restore(station_id: str, delay_s: float) -> None:
    """Auto-restore link after delay_s seconds."""
    await asyncio.sleep(delay_s)
    proxy_name = f"{station_id}-mqtt"
    await _client.enable_proxy(proxy_name)
    log.info("link_sim.auto_restore", station_id=station_id, delay_s=delay_s)


@app.post("/link/restore")
async def restore_link(req: RestoreRequest) -> Dict[str, Any]:
    """Re-enable satellite link for one or both stations."""
    _require_client()
    stations = _stations_from(req.station_id)
    for station_id in stations:
        proxy_name = f"{station_id}-mqtt"
        # Cancel pending auto-restore
        task = _outage_tasks.get(station_id)
        if task and not task.done():
            task.cancel()
        await _client.enable_proxy(proxy_name)
    log.info("link_sim.link_restored", stations=stations)
    return {"restored": stations}


@app.post("/link/degrade")
async def degrade_link(req: DegradeRequest) -> Dict[str, Any]:
    """Apply degraded link conditions (latency + bandwidth limit)."""
    _require_client()
    stations = _stations_from(req.station_id)
    for station_id in stations:
        proxy_name = f"{station_id}-mqtt"
        # Remove existing toxics first
        toxics = await _client.list_toxics(proxy_name)
        for t in toxics:
            await _client.remove_toxic(proxy_name, t["name"])
        await _client.add_latency_toxic(
            proxy_name, req.latency_ms, req.jitter_ms, toxic_name="deg_latency"
        )
        await _client.add_bandwidth_toxic(
            proxy_name, req.bandwidth_kbps, toxic_name="deg_bandwidth"
        )
    return {
        "degraded": stations,
        "latency_ms": req.latency_ms,
        "bandwidth_kbps": req.bandwidth_kbps,
    }


@app.post("/link/reset")
async def reset_link(req: RestoreRequest) -> Dict[str, Any]:
    """Remove all toxics and restore default satellite latency for a station."""
    _require_client()
    stations = _stations_from(req.station_id)
    for station_id in stations:
        proxy_name = f"{station_id}-mqtt"
        await _client.reset_proxy(proxy_name)
        # Re-apply default satellite latency
        await _client.add_latency_toxic(proxy_name, latency_ms=800, jitter_ms=200)
    return {"reset": stations, "note": "Default 800ms satellite latency restored"}
