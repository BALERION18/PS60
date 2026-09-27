"""Cloud ingestion service — receives, verifies, and stores SyncEnvelopes.

Pipeline for each received MQTT message:
  1. JSON-parse the envelope dict
  2. Verify Ed25519 signature with the station's public key
  3. zstd-decompress to get the original payload dict
  4. Route by message_type to the appropriate handler
  5. Write to Cloud TimescaleDB / PostgreSQL

Idempotency:
  - Sensor readings: INSERT (duplicates may occur from retry; TimescaleDB handles)
  - Alerts: INSERT ... ON CONFLICT (alert_id) DO NOTHING
  - Black-box frames: INSERT ... ON CONFLICT (event_id, frame_index) DO NOTHING
  - Station connections: UPSERT by station_id

All handlers are async and share a per-message DB session.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.crypto.signing import VerificationError, Verifier
from shared.db.models.cloud import StationConnection
from shared.db.models.edge import Alert, BlackBoxFrame, SensorReading
from shared.utils.time import utcnow
from cloud.redis_client import cloud_alerts_channel, get_redis, station_status_channel
from edge.sync_agent.envelope import unpack_envelope

log = structlog.get_logger(__name__)


class CloudIngestionService:
    """Routes incoming SyncEnvelopes to Cloud DB tables."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        verifiers: Dict[str, Verifier],  # station_id → Verifier
    ) -> None:
        self._session_factory = session_factory
        self._verifiers = verifiers

    async def receive_envelope(
        self,
        envelope: Dict[str, Any],
        station_id: str,
    ) -> None:
        """Verify, decompress, and store one SyncEnvelope.

        Args:
            envelope: Parsed SyncEnvelope dict from MQTT.
            station_id: Station that sent the envelope (from MQTT topic).
        """
        # 1. Verify station_id matches envelope claim
        if envelope.get("station_id") != station_id:
            log.warning(
                "cloud.ingestion.station_id_mismatch",
                topic_station=station_id,
                envelope_station=envelope.get("station_id"),
            )
            return

        # 2. Verify signature
        verifier = self._verifiers.get(station_id)
        if verifier is None:
            log.error("cloud.ingestion.no_verifier", station_id=station_id)
            return

        try:
            payload = unpack_envelope(envelope, verifier)
        except VerificationError as exc:
            log.error(
                "cloud.ingestion.signature_invalid",
                station_id=station_id,
                error=str(exc),
            )
            return
        except Exception as exc:
            log.error("cloud.ingestion.unpack_error", station_id=station_id, error=str(exc))
            return

        # 3. Route by message_type
        message_type = envelope.get("message_type", "")
        async with self._session_factory() as session:
            try:
                if message_type == "SENSOR_BATCH":
                    await self._handle_sensor_batch(payload, station_id, session)
                elif message_type.startswith("ALERT"):
                    await self._handle_alert(payload, station_id, session)
                elif message_type == "BLACK_BOX_FRAME":
                    await self._handle_black_box_frame(payload, station_id, session)
                elif message_type == "LINK_HEARTBEAT":
                    await self._handle_link_heartbeat(payload, station_id, session)
                elif message_type == "INVENTORY_SNAPSHOT":
                    log.debug("cloud.ingestion.inventory_snapshot", station_id=station_id)
                else:
                    log.warning("cloud.ingestion.unknown_type", message_type=message_type)
                await session.commit()
            except Exception as exc:
                log.error(
                    "cloud.ingestion.handler_error",
                    message_type=message_type,
                    station_id=station_id,
                    error=str(exc),
                )
                await session.rollback()

    # ---------------------------------------------------------------------------
    # Handlers
    # ---------------------------------------------------------------------------

    async def _handle_sensor_batch(
        self, payload: Dict[str, Any], station_id: str, session: AsyncSession
    ) -> None:
        """Bulk-insert sensor readings into Cloud TimescaleDB."""
        readings = payload.get("readings", [])
        if not readings:
            return

        rows = []
        for r in readings:
            ts_raw = r.get("timestamp_utc", "")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = utcnow()
            rows.append({
                "station_id": station_id,
                "sensor_id": r.get("sensor_id", ""),
                "domain": r.get("domain", ""),
                "metric_name": r.get("metric_name", ""),
                "value": float(r.get("value", 0.0)),
                "unit": r.get("unit", ""),
                "quality": r.get("quality", "NOMINAL"),
                "asset_id": r.get("asset_id") or None,
                "timestamp_utc": ts,
                "is_aggregate": r.get("is_aggregate", False),
                "aggregation_window_s": r.get("aggregation_window_s") or None,
            })

        await session.execute(SensorReading.__table__.insert(), rows)
        log.info("cloud.ingestion.sensor_batch", station_id=station_id, count=len(rows))

    async def _handle_alert(
        self, payload: Dict[str, Any], station_id: str, session: AsyncSession
    ) -> None:
        """Insert alert with ON CONFLICT DO NOTHING (idempotent by alert_id)."""
        alert_id = payload.get("alert_id", "")
        if not alert_id:
            log.warning("cloud.ingestion.alert_missing_id", station_id=station_id)
            return

        triggered_raw = payload.get("triggered_at", "")
        try:
            triggered_at = datetime.fromisoformat(triggered_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            triggered_at = utcnow()

        stmt = (
            pg_insert(Alert.__table__)
            .values(
                alert_id=alert_id,
                station_id=station_id,
                severity=payload.get("severity", "LOW"),
                domain=payload.get("domain", ""),
                asset_id=payload.get("asset_id") or None,
                triggered_at=triggered_at,
                description=payload.get("description", ""),
                raw_sensor_snapshot=payload.get("raw_sensor_snapshot"),
                ack_state=payload.get("ack_state", "OPEN"),
                acknowledged_by=payload.get("acknowledged_by") or None,
                acknowledged_at=None,
                resolved_at=None,
                black_box_activated=payload.get("black_box_activated", False),
                synced_to_cloud=True,
                created_at=utcnow(),
            )
            .on_conflict_do_nothing(index_elements=["alert_id"])
        )
        result = await session.execute(stmt)
        if result.rowcount > 0:
            log.warning(
                "cloud.ingestion.alert_received",
                alert_id=alert_id,
                station_id=station_id,
                severity=payload.get("severity"),
            )
            # Publish to WebSocket broadcast channel
            redis = get_redis()
            await redis.publish(
                cloud_alerts_channel(),
                json.dumps({**payload, "station_id": station_id}, default=str),
            )
        else:
            log.debug("cloud.ingestion.alert_duplicate", alert_id=alert_id)

    async def _handle_black_box_frame(
        self, payload: Dict[str, Any], station_id: str, session: AsyncSession
    ) -> None:
        """Insert black-box frame with ON CONFLICT DO NOTHING."""
        import base64
        frame_id = payload.get("frame_id", "")
        event_id = payload.get("event_id", "")

        ts_raw = payload.get("timestamp_utc", "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = utcnow()

        # readings_protobuf is base64-encoded JSON bytes on the wire
        readings_bytes = b""
        rb = payload.get("readings_protobuf", "")
        if isinstance(rb, str):
            try:
                readings_bytes = base64.b64decode(rb)
            except Exception:
                readings_bytes = rb.encode("utf-8")
        elif isinstance(rb, bytes):
            readings_bytes = rb

        prev_hash = bytes.fromhex(payload.get("prev_hash_hex", "00" * 32))
        frame_hash = bytes.fromhex(payload.get("frame_hash_hex", "00" * 32))

        stmt = (
            pg_insert(BlackBoxFrame.__table__)
            .values(
                frame_id=frame_id,
                event_id=event_id,
                station_id=station_id,
                trigger_alert_id=payload.get("trigger_alert_id", ""),
                frame_index=payload.get("frame_index", 0),
                readings_protobuf=readings_bytes,
                phase=payload.get("phase", "ACTIVE"),
                prev_hash=prev_hash,
                frame_hash=frame_hash,
                timestamp_utc=ts,
                is_partial_pre_event=payload.get("is_partial_pre_event", False),
                window_closed=payload.get("window_closed", False),
                synced_to_cloud=True,
            )
            .on_conflict_do_nothing(index_elements=["event_id", "frame_index"])
        )
        await session.execute(stmt)
        log.info("cloud.ingestion.black_box_frame", event_id=event_id, station_id=station_id)

    async def _handle_link_heartbeat(
        self, payload: Dict[str, Any], station_id: str, session: AsyncSession
    ) -> None:
        """Upsert station connection status from heartbeat."""
        now = utcnow()
        link_state = payload.get("link_state", "UP")
        queue_depth = payload.get("queue_depth", 0)

        stmt = (
            pg_insert(StationConnection.__table__)
            .values(
                station_id=station_id,
                last_heartbeat_at=now,
                link_state=link_state,
                queue_depth_bytes=queue_depth,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["station_id"],
                set_={
                    "last_heartbeat_at": now,
                    "link_state": link_state,
                    "queue_depth_bytes": queue_depth,
                    "updated_at": now,
                },
            )
        )
        await session.execute(stmt)

        # Publish station status update to WebSocket broadcast
        redis = get_redis()
        await redis.publish(
            station_status_channel(station_id),
            json.dumps({
                "station_id": station_id,
                "link_state": link_state,
                "last_heartbeat_at": now.isoformat(),
                "queue_depth": queue_depth,
            }),
        )
        log.debug("cloud.ingestion.heartbeat", station_id=station_id, link_state=link_state)
