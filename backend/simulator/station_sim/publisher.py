"""Sensor publisher — sends batched readings to the Edge ingestion service.

In Phase 1 (standalone), the publisher logs readings locally if the
Edge HTTP endpoint is not yet running. From Phase 2 onwards, it POSTs
JSON batches to the Edge ingestion service.

The publisher buffers readings by domain and flushes each domain's batch
at the configured batch window interval (e.g., every 10 seconds in dev).
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from typing import Any, Dict, List

import httpx
import structlog

from shared.utils.time import utcnow

log = structlog.get_logger(__name__)

# Default Edge ingestion endpoint (overridden by EDGE_INGEST_URL env var)
DEFAULT_INGEST_URL = "http://localhost:8100/ingest"


class SensorPublisher:
    """Buffers sensor readings and flushes them to the Edge ingestion endpoint.

    Usage:
        publisher = SensorPublisher(station_id="maitri")
        publisher.add_readings(readings)  # called each tick
        await publisher.flush()            # called each batch-window tick
    """

    def __init__(
        self,
        station_id: str,
        ingest_url: str | None = None,
        batch_window_s: float = 10.0,
        dry_run: bool = False,
    ) -> None:
        self.station_id = station_id
        self.ingest_url = ingest_url or os.getenv("EDGE_INGEST_URL", DEFAULT_INGEST_URL)
        self.batch_window_s = batch_window_s
        self.dry_run = dry_run  # if True, log readings instead of POSTing

        self._buffer: List[Dict[str, Any]] = []
        self._total_sent = 0
        self._total_failed = 0
        self._last_flush_at = utcnow()
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Initialize the HTTP client. Call at service startup."""
        self._client = httpx.AsyncClient(timeout=10.0)

    async def stop(self) -> None:
        """Flush remaining readings and close the HTTP client."""
        if self._buffer:
            await self.flush()
        if self._client:
            await self._client.aclose()

    def add_readings(self, readings: List[Dict[str, Any]]) -> None:
        """Add readings to the local buffer. Thread-safe (called from async context)."""
        self._buffer.extend(readings)

    async def flush(self) -> bool:
        """Send all buffered readings to the Edge ingestion service.

        Returns:
            True if flush succeeded (or dry_run), False on HTTP error.
        """
        if not self._buffer:
            return True

        batch = {
            "station_id": self.station_id,
            "readings": list(self._buffer),
            "generated_at": utcnow().isoformat(),
            "is_aggregate": False,
        }
        self._buffer.clear()
        self._last_flush_at = utcnow()

        if self.dry_run:
            log.info(
                "sim.publisher.dry_run",
                station_id=self.station_id,
                reading_count=len(batch["readings"]),
            )
            self._total_sent += len(batch["readings"])
            return True

        try:
            resp = await self._client.post(
                self.ingest_url,
                content=json.dumps(batch, default=str),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            self._total_sent += len(batch["readings"])
            log.debug(
                "sim.publisher.sent",
                station_id=self.station_id,
                reading_count=len(batch["readings"]),
                status=resp.status_code,
            )
            return True
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            self._total_failed += len(batch["readings"])
            log.warning(
                "sim.publisher.send_failed",
                station_id=self.station_id,
                error=str(exc),
                reading_count=len(batch["readings"]),
                note="Edge ingestion service not reachable — readings discarded in Phase 1",
            )
            return False

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_sent": self._total_sent,
            "total_failed": self._total_failed,
            "buffer_depth": len(self._buffer),
            "last_flush_at": self._last_flush_at.isoformat(),
        }
