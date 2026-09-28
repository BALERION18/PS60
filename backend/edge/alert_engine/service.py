"""Edge Alert Engine — subscribes to Redis sensor channels and evaluates rules.

Architecture:
  - Subscribes to Redis pub/sub channels: sensor:{station_id}:*
  - For each reading received, runs ThresholdEvaluator against station config rules
  - De-duplicates: if a rule is already OPEN for that sensor, no new alert is raised
  - Creates Alert rows in DB and publishes to alerts:{station_id} for black-box logger
  - Auto-resolves non-CRITICAL alerts when the sensor returns to normal range
  - CRITICAL alerts require manual resolution (via Edge local API PATCH)
  - Tracks previous sensor values for rate-of-change evaluation

Redis keys used:
  - dedup:alert:{station_id}:{rule_id}:{sensor_id}  TTL={dedup_ttl_s}
    Value: alert_id of the open alert
  - sensor_prev:{station_id}:{sensor_id}
    Value: JSON {"value": float, "ts": ISO string} — for rate-of-change calc
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models.edge import Alert
from shared.schemas.config import AlertSeverity, StationConfig
from shared.utils.alert_id import generate_alert_id
from shared.utils.time import utcnow
from edge.alert_engine.evaluator import AlertCandidate, evaluate_thresholds
from edge.redis_client import alerts_channel, dedup_key, get_redis, sensor_channel

log = structlog.get_logger(__name__)


class AlertEngine:
    """Background service: consumes sensor readings and raises/resolves alerts."""

    def __init__(
        self,
        station_id: str,
        config: StationConfig,
        session_factory: async_sessionmaker[AsyncSession],
        dedup_ttl_s: int = 300,
    ) -> None:
        self._station_id = station_id
        self._config = config
        self._session_factory = session_factory
        self._dedup_ttl_s = dedup_ttl_s
        self._task: Optional[asyncio.Task] = None
        self._running = False
        # Cache: sensor_id → (prev_value, prev_ts)
        self._prev_values: Dict[str, tuple[float, datetime]] = {}

    async def start(self) -> None:
        """Start the background alert processing loop."""
        self._running = True
        self._task = asyncio.create_task(self._run(), name="alert-engine")
        log.info("edge.alert_engine.started", station_id=self._station_id)

    async def stop(self) -> None:
        """Gracefully stop the alert engine."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("edge.alert_engine.stopped", station_id=self._station_id)

    async def _run(self) -> None:
        """Subscribe to all sensor channels for this station and process readings."""
        redis = get_redis()
        # Subscribe to all domain channels for this station
        domains = {s.domain.value for s in self._config.sensors}
        channels = [sensor_channel(self._station_id, d) for d in domains]

        pubsub = redis.pubsub()
        await pubsub.subscribe(*channels)
        log.info("edge.alert_engine.subscribed", channels=channels)

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
                    log.error("edge.alert_engine.read_error", error=str(exc))
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    async def _process_reading(self, reading: Dict[str, Any]) -> None:
        """Evaluate rules against one reading, raise or auto-resolve alerts."""
        candidates = evaluate_thresholds(reading, self._config.threshold_rules)

        async with self._session_factory() as session:
            for candidate in candidates:
                await self._handle_candidate(candidate, reading, session)
            # Auto-resolution: check if any OPEN alert's rule is no longer breached
            await self._check_auto_resolve(reading, candidates, session)
            await session.commit()

        # Update prev value cache for rate-of-change
        self._prev_values[reading["sensor_id"]] = (
            reading["value"],
            datetime.fromisoformat(reading["timestamp_utc"].replace("Z", "+00:00"))
        )

    async def _handle_candidate(
        self,
        candidate: AlertCandidate,
        reading: Dict[str, Any],
        session: AsyncSession,
    ) -> None:
        """Raise an alert for a candidate if not already de-duplicated."""
        redis = get_redis()
        dkey = dedup_key(self._station_id, candidate.rule_id, candidate.sensor_id)

        # Check dedup cache — if key exists, alert is already OPEN
        existing_alert_id = await redis.get(dkey)
        if existing_alert_id:
            return  # already open, skip

        # Create the alert
        alert_id = generate_alert_id(self._station_id, candidate.domain)
        now = utcnow()

        snapshot = {
            "sensor_id": reading["sensor_id"],
            "value": reading["value"],
            "unit": reading.get("unit", ""),
            "quality": reading.get("quality", "NOMINAL"),
            "timestamp_utc": reading["timestamp_utc"],
            "threshold_value": candidate.threshold_value,
            "condition": candidate.condition,
        }

        alert = Alert(
            alert_id=alert_id,
            station_id=self._station_id,
            severity=candidate.severity.value,
            domain=candidate.domain,
            asset_id=candidate.asset_id,
            triggered_at=now,
            description=candidate.description,
            raw_sensor_snapshot=snapshot,
            ack_state="OPEN",
            black_box_activated=False,
            synced_to_cloud=False,
            created_at=now,
        )
        session.add(alert)

        # Set dedup key (TTL = dedup_ttl_s; refreshed on subsequent same-rule readings)
        await redis.set(dkey, alert_id, ex=self._dedup_ttl_s)

        log.warning(
            "edge.alert.raised",
            alert_id=alert_id,
            station_id=self._station_id,
            severity=candidate.severity.value,
            sensor_id=candidate.sensor_id,
            description=candidate.description,
        )

        # Publish to alerts channel for black-box logger
        alert_payload = {
            "alert_id": alert_id,
            "station_id": self._station_id,
            "severity": candidate.severity.value,
            "domain": candidate.domain,
            "asset_id": candidate.asset_id,
            "triggered_at": now.isoformat(),
            "description": candidate.description,
            "ack_state": "OPEN",
        }
        await redis.publish(alerts_channel(self._station_id), json.dumps(alert_payload))

    async def _check_auto_resolve(
        self,
        reading: Dict[str, Any],
        active_candidates: List[AlertCandidate],
        session: AsyncSession,
    ) -> None:
        """Auto-resolve non-CRITICAL open alerts whose threshold is no longer breached.

        CRITICAL alerts always require manual resolution via the API.
        """
        redis = get_redis()
        sensor_id = reading["sensor_id"]

        # Find candidate rule_ids that are still breached for this sensor
        still_breached_rule_ids = {c.rule_id for c in active_candidates}

        # Check all dedup keys for this sensor
        pattern = dedup_key(self._station_id, "*", sensor_id)
        cursor = 0
        keys: list[str] = []
        while True:
            cursor, batch = await redis.scan(cursor, match=pattern, count=100)
            keys.extend([k.decode() if isinstance(k, bytes) else k for k in batch])
            if cursor == 0:
                break

        for key in keys:
            # Extract rule_id from key format: dedup:alert:{sid}:{rule_id}:{sensor_id}
            parts = key.split(":", maxsplit=3)
            if len(parts) < 4:
                continue
            # parts[3] = "{rule_id}:{sensor_id}"
            remainder = parts[3]
            # rule_id ends at last colon separator before sensor_id
            rule_id = remainder.rsplit(":", maxsplit=1)[0] if ":" in remainder else remainder

            if rule_id in still_breached_rule_ids:
                continue  # still breached, no resolution

            existing_alert_id = await redis.get(key)
            if not existing_alert_id:
                continue
            alert_id_str = (
                existing_alert_id.decode()
                if isinstance(existing_alert_id, bytes)
                else existing_alert_id
            )

            # Look up the alert — only auto-resolve non-CRITICAL
            result = await session.execute(
                select(Alert).where(Alert.alert_id == alert_id_str)
            )
            alert = result.scalar_one_or_none()
            if alert is None or alert.ack_state == "RESOLVED":
                await redis.delete(key)
                continue
            if alert.severity == AlertSeverity.CRITICAL.value:
                # CRITICAL: refresh the dedup TTL but don't auto-resolve
                await redis.expire(key, self._dedup_ttl_s)
                continue

            # Auto-resolve
            alert.ack_state = "RESOLVED"
            alert.resolved_at = utcnow()
            await redis.delete(key)

            log.info(
                "edge.alert.auto_resolved",
                alert_id=alert_id_str,
                station_id=self._station_id,
                sensor_id=sensor_id,
            )

            # Publish resolution event
            resolution_payload = {
                "alert_id": alert_id_str,
                "station_id": self._station_id,
                "ack_state": "RESOLVED",
                "resolved_at": utcnow().isoformat(),
                "auto_resolved": True,
            }
            await redis.publish(
                alerts_channel(self._station_id),
                json.dumps(resolution_payload),
            )
