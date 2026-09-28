"""Edge AI Engine service — real-time inference on incoming sensor readings.

Architecture:
  - Subscribes to Redis pub/sub channel: sensor:{station_id}:energy
  - For each reading, updates two per-asset accumulators:
      • StateBuffer      (Model 2 — Isolation Forest vibration features)
      • AssetState       (Model 4 — Maintenance features: rolling trends + counters)
  - On every vibration_rms reading:
      1. Run VibrationAnomalyModel.predict()   → anomaly score + risk_level
      2. Feed the IF score into AssetState.update_anomaly()
      3. If anomaly detected (WARNING/CRITICAL), run MaintenanceModel.predict()
         → urgency + days_until_action + recommended_task
  - If anomaly is WARNING/CRITICAL:
      • Set dedup key in Redis (TTL=5min) to suppress duplicate events
      • Publish to Redis channel: ai_anomaly:{station_id}
        Payload includes both the anomaly result AND the maintenance prediction
      • Persist to DB (fire-and-forget, failure is non-fatal)
  - If maintenance urgency is MEDIUM/HIGH (even without active anomaly):
      • Publish to Redis channel: ai_maintenance:{station_id}

Both models degrade gracefully:
  - Missing model file → service starts, logs warning, inference skipped
  - Both can be trained independently and hot-reloaded (future work)

Redis keys:
  - ai_dedup:{station_id}:{asset_id}        TTL=dedup_ttl_s
  - ai_maint_dedup:{station_id}:{asset_id}  TTL=maint_dedup_ttl_s (longer — 30 min)
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from edge.ai_engine.feature_builder import (
    FEATURE_SPEC,
    StateBuffer,
    asset_id_from_sensor,
    extract_suffix,
    is_generator_sensor,
)
from edge.ai_engine.maintenance_features import AssetState
from edge.ai_engine.maintenance_model import MaintenanceModel, MaintenancePrediction
from edge.ai_engine.vibration_model import AnomalyPrediction, VibrationAnomalyModel
from edge.redis_client import get_redis, sensor_channel

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Redis channel / key helpers
# ---------------------------------------------------------------------------
AI_ANOMALY_CHANNEL_PREFIX   = "ai_anomaly"
AI_MAINT_CHANNEL_PREFIX     = "ai_maintenance"
AI_DEDUP_KEY_PREFIX         = "ai_dedup"
AI_MAINT_DEDUP_KEY_PREFIX   = "ai_maint_dedup"

DEFAULT_DEDUP_TTL_S         = 300     # 5 min  — anomaly dedup
DEFAULT_MAINT_DEDUP_TTL_S   = 1800    # 30 min — maintenance dedup (less urgent)


def ai_anomaly_channel(station_id: str) -> str:
    return f"{AI_ANOMALY_CHANNEL_PREFIX}:{station_id}"


def ai_maintenance_channel(station_id: str) -> str:
    return f"{AI_MAINT_CHANNEL_PREFIX}:{station_id}"


def ai_dedup_key(station_id: str, asset_id: str) -> str:
    return f"{AI_DEDUP_KEY_PREFIX}:{station_id}:{asset_id}"


def ai_maint_dedup_key(station_id: str, asset_id: str) -> str:
    return f"{AI_MAINT_DEDUP_KEY_PREFIX}:{station_id}:{asset_id}"


# ---------------------------------------------------------------------------
# AIEngineService
# ---------------------------------------------------------------------------

class AIEngineService:
    """Background service: runs Model 2 (Isolation Forest) and Model 4 (Maintenance RF).

    Lifecycle:
        await service.start()   # called in edge/main.py lifespan
        ...app runs...
        await service.stop()    # called on shutdown
    """

    def __init__(
        self,
        station_id: str,
        session_factory: async_sessionmaker[AsyncSession],
        dedup_ttl_s: int       = DEFAULT_DEDUP_TTL_S,
        maint_dedup_ttl_s: int = DEFAULT_MAINT_DEDUP_TTL_S,
    ) -> None:
        self._station_id        = station_id
        self._session_factory   = session_factory
        self._dedup_ttl_s       = dedup_ttl_s
        self._maint_dedup_ttl_s = maint_dedup_ttl_s

        # Model 2 — Isolation Forest
        self._vib_model: Optional[VibrationAnomalyModel] = None
        # Model 4 — Maintenance Random Forest
        self._maint_model: Optional[MaintenanceModel] = None

        # Per-asset accumulators
        self._vib_buffers: Dict[str, StateBuffer]  = {}   # asset_id → vibration StateBuffer
        self._asset_states: Dict[str, AssetState]  = {}   # asset_id → maintenance AssetState

        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Load both models and start the background inference loop."""
        # Model 2 — Isolation Forest
        self._vib_model = VibrationAnomalyModel.load_or_none()
        if self._vib_model is None:
            log.warning(
                "ai_engine.vibration_model_missing",
                station_id=self._station_id,
                hint="Run: python -m scripts.train_vibration_model",
            )
        else:
            meta = self._vib_model.metadata
            log.info(
                "ai_engine.vibration_model_loaded",
                station_id=self._station_id,
                trained_at=meta.trained_at if meta else "unknown",
            )

        # Model 4 — Maintenance RF
        self._maint_model = MaintenanceModel.load_or_none()
        if self._maint_model is None:
            log.warning(
                "ai_engine.maintenance_model_missing",
                station_id=self._station_id,
                hint="Run: python -m scripts.train_maintenance_model",
            )
        else:
            meta = self._maint_model.metadata
            log.info(
                "ai_engine.maintenance_model_loaded",
                station_id=self._station_id,
                trained_at=meta.trained_at if meta else "unknown",
            )

        self._running = True
        self._task = asyncio.create_task(self._run(), name="ai-engine")
        log.info(
            "ai_engine.started",
            station_id=self._station_id,
            vibration_model=self._vib_model is not None,
            maintenance_model=self._maint_model is not None,
        )

    async def stop(self) -> None:
        """Gracefully stop the AI engine."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("ai_engine.stopped", station_id=self._station_id)

    # ------------------------------------------------------------------
    # Main Redis subscription loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Subscribe to energy sensor channel and process each reading."""
        if self._vib_model is None and self._maint_model is None:
            log.warning(
                "ai_engine.skipping_inference",
                reason="no_models_loaded",
                station_id=self._station_id,
            )
            return

        redis   = get_redis()
        channel = sensor_channel(self._station_id, "energy")
        pubsub  = redis.pubsub()
        await pubsub.subscribe(channel)
        log.info("ai_engine.subscribed", channel=channel)

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                try:
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    reading = json.loads(data)
                    await self._process_reading(reading)
                except Exception as exc:
                    log.error(
                        "ai_engine.read_error",
                        error=str(exc),
                        station_id=self._station_id,
                    )
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    # ------------------------------------------------------------------
    # Per-reading processing
    # ------------------------------------------------------------------

    async def _process_reading(self, reading: Dict[str, Any]) -> None:
        """Route an incoming sensor reading to both model accumulators."""
        sensor_id = reading.get("sensor_id", "")
        if not is_generator_sensor(sensor_id):
            return

        asset_id = asset_id_from_sensor(sensor_id)
        suffix   = extract_suffix(sensor_id)
        value    = float(reading.get("value", 0.0))

        # --- Update Model 2 StateBuffer ---
        if asset_id not in self._vib_buffers:
            self._vib_buffers[asset_id] = StateBuffer(asset_id=asset_id)
        vib_buf = self._vib_buffers[asset_id]
        vib_buf.update(suffix, value)

        # --- Update Model 4 AssetState ---
        if asset_id not in self._asset_states:
            self._asset_states[asset_id] = AssetState(asset_id=asset_id)
        asset_state = self._asset_states[asset_id]
        asset_state.update_sensor(suffix, value)

        # Trigger inference on every vibration_rms reading
        # (vibration is the primary signal that gates the pipeline)
        if suffix == "vibration_rms":
            vib_buf.flush()
            await self._run_pipeline(asset_id, vib_buf, asset_state)

    async def _run_pipeline(
        self,
        asset_id: str,
        vib_buf: StateBuffer,
        asset_state: AssetState,
    ) -> None:
        """Run Model 2 → Model 4 inference pipeline for one asset."""
        if not vib_buf.is_ready:
            return

        # ---- Step 1: Model 2 — Vibration Anomaly (Isolation Forest) ----
        anom_pred: Optional[AnomalyPrediction] = None
        if self._vib_model is not None:
            latest_vec = vib_buf.get_latest_vector()
            if latest_vec is not None:
                # Denormalise from [0,1] back to raw physical values
                readings: Dict[str, float] = {
                    name: float(latest_vec[i] * clip_max)
                    for i, (name, _, clip_max, _) in enumerate(FEATURE_SPEC)
                }
                anom_pred = self._vib_model.predict(
                    asset_id=asset_id,
                    readings=readings,
                )
                # Feed the IF score into the maintenance accumulator
                asset_state.update_anomaly(
                    if_score=anom_pred.anomaly_score,
                    is_anomaly=anom_pred.is_anomaly,
                )

        # ---- Step 2: Model 4 — Predictive Maintenance (Random Forest) ----
        maint_pred: Optional[MaintenancePrediction] = None
        if self._maint_model is not None:
            # Always compute maintenance prediction (not gated on anomaly)
            # so we catch runtime-hours-based triggers even without active anomalies
            feature_dict = asset_state.to_feature_dict()
            maint_pred = self._maint_model.predict(
                asset_id=asset_id,
                features=feature_dict,
            )

        # ---- Step 3: Handle outputs ----
        if anom_pred is not None and anom_pred.is_anomaly:
            await self._handle_anomaly(anom_pred, maint_pred)

        if maint_pred is not None and maint_pred.is_urgent:
            await self._handle_maintenance(maint_pred)

    # ------------------------------------------------------------------
    # Anomaly handler — Model 2 output
    # ------------------------------------------------------------------

    async def _handle_anomaly(
        self,
        anom_pred: AnomalyPrediction,
        maint_pred: Optional[MaintenancePrediction],
    ) -> None:
        """Dedup, publish, and persist a vibration anomaly event."""
        redis = get_redis()
        dkey  = ai_dedup_key(self._station_id, anom_pred.asset_id)

        existing = await redis.get(dkey)
        if existing:
            await redis.expire(dkey, self._dedup_ttl_s)
            return

        now = datetime.now(tz=timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "event_type":    "anomaly",
            "station_id":    self._station_id,
            "asset_id":      anom_pred.asset_id,
            "anomaly_score": round(anom_pred.anomaly_score, 4),
            "risk_level":    anom_pred.risk_level,
            "confidence":    round(anom_pred.confidence, 4),
            "model_name":    anom_pred.model_name,
            "model_version": anom_pred.model_version,
            "sensor_readings": {
                k: round(v, 3) for k, v in anom_pred.sensor_readings.items()
            },
            "detected_at":   now,
        }

        # Enrich with maintenance prediction if available
        if maint_pred is not None:
            payload["maintenance"] = {
                "urgency":           maint_pred.urgency,
                "days_until_action": maint_pred.days_until_action,
                "recommended_task":  maint_pred.recommended_task,
                "confidence":        round(maint_pred.confidence, 4),
            }

        await redis.publish(
            ai_anomaly_channel(self._station_id),
            json.dumps(payload),
        )
        await redis.set(
            dkey,
            json.dumps({"risk_level": anom_pred.risk_level, "score": anom_pred.anomaly_score}),
            ex=self._dedup_ttl_s,
        )

        await self._persist_anomaly(anom_pred, maint_pred)

        log.warning(
            "ai_engine.anomaly_published",
            station_id=self._station_id,
            asset_id=anom_pred.asset_id,
            risk_level=anom_pred.risk_level,
            score=round(anom_pred.anomaly_score, 4),
            maintenance_urgency=maint_pred.urgency if maint_pred else "N/A",
            days_until_action=maint_pred.days_until_action if maint_pred else None,
        )

    # ------------------------------------------------------------------
    # Maintenance handler — Model 4 output (MEDIUM/HIGH, no anomaly needed)
    # ------------------------------------------------------------------

    async def _handle_maintenance(self, maint_pred: MaintenancePrediction) -> None:
        """Publish a maintenance recommendation when urgency is MEDIUM or HIGH."""
        redis = get_redis()
        dkey  = ai_maint_dedup_key(self._station_id, maint_pred.asset_id)

        existing = await redis.get(dkey)
        if existing:
            await redis.expire(dkey, self._maint_dedup_ttl_s)
            return

        payload: Dict[str, Any] = {
            "event_type":        "maintenance",
            "station_id":        self._station_id,
            "asset_id":          maint_pred.asset_id,
            "urgency":           maint_pred.urgency,
            "days_until_action": maint_pred.days_until_action,
            "recommended_task":  maint_pred.recommended_task,
            "confidence":        round(maint_pred.confidence, 4),
            "class_probabilities": maint_pred.class_probabilities,
            "model_name":        maint_pred.model_name,
            "model_version":     maint_pred.model_version,
            "detected_at":       datetime.now(tz=timezone.utc).isoformat(),
        }

        await redis.publish(
            ai_maintenance_channel(self._station_id),
            json.dumps(payload),
        )
        await redis.set(
            dkey,
            json.dumps({"urgency": maint_pred.urgency}),
            ex=self._maint_dedup_ttl_s,
        )

        log.warning(
            "ai_engine.maintenance_published",
            station_id=self._station_id,
            asset_id=maint_pred.asset_id,
            urgency=maint_pred.urgency,
            days_until_action=maint_pred.days_until_action,
            task=maint_pred.recommended_task,
        )

    # ------------------------------------------------------------------
    # DB persistence (fire-and-forget)
    # ------------------------------------------------------------------

    async def _persist_anomaly(
        self,
        anom_pred: AnomalyPrediction,
        maint_pred: Optional[MaintenancePrediction],
    ) -> None:
        """Write anomaly + optional maintenance result to Edge DB."""
        try:
            async with self._session_factory() as session:
                # We use a generic JSON insert since the Edge DB doesn't yet
                # have a dedicated ai_anomaly_scores table.
                # The cloud sync agent will pick this up via the existing
                # outbound queue once that table is added in a migration.
                from sqlalchemy import text
                from shared.utils.time import utcnow

                await session.execute(
                    text("""
                        INSERT INTO audit_log
                            (entry_id, station_id, actor_id, action,
                             resource_type, resource_id, timestamp_utc)
                        VALUES
                            (:eid, :sid, 'ai_engine', 'AI_ANOMALY_DETECTED',
                             'asset', :rid, :ts)
                    """),
                    {
                        "eid": _new_uuid(),
                        "sid": self._station_id,
                        "rid": anom_pred.asset_id,
                        "ts":  utcnow(),
                    },
                )
                await session.commit()
        except Exception as exc:
            # Non-fatal — anomaly already published to Redis
            log.error(
                "ai_engine.persist_failed",
                error=str(exc),
                asset_id=anom_pred.asset_id,
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_model_loaded(self) -> bool:
        """True if at least the vibration model is loaded."""
        return self._vib_model is not None and self._vib_model.is_loaded

    @property
    def both_models_loaded(self) -> bool:
        return (
            self._vib_model is not None
            and self._vib_model.is_loaded
            and self._maint_model is not None
            and self._maint_model.is_loaded
        )

    @property
    def model_metadata(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self._vib_model and self._vib_model.metadata:
            result["vibration_anomaly"] = self._vib_model.metadata.to_dict()
        if self._maint_model and self._maint_model.metadata:
            result["predictive_maintenance"] = self._maint_model.metadata.to_dict()
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_uuid() -> str:
    import uuid
    return str(uuid.uuid4())
