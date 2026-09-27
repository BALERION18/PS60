"""Edge ingestion service — writes sensor batches to TimescaleDB and Redis.

Receives SensorBatch JSON from the station simulator (Phase 1) or from
any future hardware driver. For each reading in the batch:
  1. Inserts a row into `sensor_readings` (bulk insert, one transaction per batch)
  2. Publishes the reading as JSON to the appropriate Redis pub/sub channel
     so the Alert Engine and Edge AI Engine can consume it in real-time.

The HTTP endpoint returns 202 Accepted immediately — the DB write and
Redis publish happen within the request (not in a background task) so
that the response only returns after persistence is confirmed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.edge import SensorReading
from edge.redis_client import get_redis, sensor_channel

log = structlog.get_logger(__name__)


class IngestionService:
    """Handles a single SensorBatch: validates, persists, and publishes."""

    def __init__(self, session: AsyncSession, station_id: str) -> None:
        self._session = session
        self._station_id = station_id

    async def ingest(self, batch: Dict[str, Any]) -> int:
        """Persist all readings from a batch and publish to Redis.

        Args:
            batch: SensorBatch-compatible dict from the simulator or hardware driver.

        Returns:
            Number of readings successfully ingested.

        Raises:
            ValueError: If batch station_id doesn't match this Edge's station_id.
        """
        batch_station = batch.get("station_id", "")
        if batch_station != self._station_id:
            raise ValueError(
                f"Batch station_id {batch_station!r} does not match "
                f"this Edge station {self._station_id!r}"
            )

        readings: List[Dict[str, Any]] = batch.get("readings", [])
        if not readings:
            return 0

        # 1. Bulk insert into sensor_readings
        rows = [_reading_to_row(r) for r in readings]
        await self._session.execute(
            SensorReading.__table__.insert(),
            rows,
        )
        # session auto-commits via the async context manager in the router

        # 2. Publish to Redis pub/sub (grouped by domain for efficient routing)
        await self._publish_readings(readings)

        log.info(
            "edge.ingestion.batch_ingested",
            station_id=self._station_id,
            count=len(readings),
            batch_id=batch.get("batch_id", ""),
        )
        return len(readings)

    async def _publish_readings(self, readings: List[Dict[str, Any]]) -> None:
        """Publish readings to Redis pub/sub channels grouped by domain."""
        redis = get_redis()
        # Group by domain to minimise publish calls
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for r in readings:
            domain = r.get("domain", "unknown")
            by_domain.setdefault(domain, []).append(r)

        for domain, domain_readings in by_domain.items():
            channel = sensor_channel(self._station_id, domain)
            for reading in domain_readings:
                await redis.publish(channel, json.dumps(reading, default=str))


def _reading_to_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a SensorReading dict to a SQLAlchemy insert row dict."""
    ts_raw = r.get("timestamp_utc")
    if isinstance(ts_raw, str):
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    elif isinstance(ts_raw, datetime):
        ts = ts_raw
    else:
        ts = datetime.now(tz=timezone.utc)

    return {
        "station_id": r["station_id"],
        "sensor_id": r["sensor_id"],
        "domain": r.get("domain", ""),
        "metric_name": r.get("metric_name", ""),
        "value": float(r["value"]),
        "unit": r.get("unit", ""),
        "quality": r.get("quality", "NOMINAL"),
        "asset_id": r.get("asset_id") or None,
        "timestamp_utc": ts,
        "is_aggregate": r.get("is_aggregate", False),
        "aggregation_window_s": r.get("aggregation_window_s") or None,
    }
