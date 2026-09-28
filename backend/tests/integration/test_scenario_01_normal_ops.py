"""Integration Scenario 01 — Normal Operations Data Flow.

Tests the full sensor ingestion pipeline:
  Simulator payload → Edge /ingest → IngestionService → DB write + Redis pub

Exercises:
  - IngestionService.ingest(batch) — correct API
  - Redis publish on ingestion (grouped by domain)
  - Station ID validation
  - Empty batch handling
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.integration.conftest import make_sensor_reading


def _make_batch(readings, station_id="maitri"):
    return {
        "station_id": station_id,
        "batch_id": "test-batch-001",
        "readings": readings,
    }


class TestEdgeIngestionPipeline:
    """Scenario 01A — Sensor batch flows through IngestionService."""

    @pytest.mark.asyncio
    async def test_single_reading_bulk_insert(self, mock_session, mock_redis):
        """A single reading gets inserted and published to Redis."""
        from edge.ingestion.service import IngestionService

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="maitri")
            batch = _make_batch([make_sensor_reading()])
            count = await svc.ingest(batch)

        assert count == 1
        mock_session.execute.assert_called_once()
        mock_redis.publish.assert_called()

    @pytest.mark.asyncio
    async def test_batch_of_ten_readings(self, mock_session, mock_redis):
        """A batch of 10 readings is bulk-inserted in one execute call."""
        from edge.ingestion.service import IngestionService

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="maitri")
            readings = [make_sensor_reading(value=float(i), offset_seconds=i) for i in range(10)]
            count = await svc.ingest(_make_batch(readings))

        assert count == 10
        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_multi_domain_grouped_publish(self, mock_session, mock_redis):
        """Readings from 3 domains → Redis published per-reading per-domain."""
        from edge.ingestion.service import IngestionService

        publish_calls = []
        mock_redis.publish = AsyncMock(side_effect=lambda ch, data: publish_calls.append(ch) or 1)

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="maitri")
            readings = [
                make_sensor_reading(sensor_id="maitri.energy.gen1.fuel_pct", domain="energy", value=45.0),
                make_sensor_reading(sensor_id="maitri.weather.temp_c", domain="weather", value=-32.5),
                make_sensor_reading(sensor_id="maitri.env.co2_ppm", domain="environment", value=412.0),
            ]
            count = await svc.ingest(_make_batch(readings))

        assert count == 3
        # Each reading published to its own domain channel
        channels = set(publish_calls)
        assert any("energy" in c for c in channels)
        assert any("weather" in c for c in channels)
        assert any("environment" in c for c in channels)

    @pytest.mark.asyncio
    async def test_empty_batch_returns_zero(self, mock_session, mock_redis):
        """An empty readings list returns 0 and makes no DB call."""
        from edge.ingestion.service import IngestionService

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="maitri")
            count = await svc.ingest(_make_batch([]))

        assert count == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_station_id_mismatch_raises(self, mock_session, mock_redis):
        """Batch for wrong station raises ValueError."""
        from edge.ingestion.service import IngestionService

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="maitri")
            batch = _make_batch([make_sensor_reading()], station_id="bharati")
            with pytest.raises(ValueError, match="station_id"):
                await svc.ingest(batch)

    @pytest.mark.asyncio
    async def test_bharati_station_ingests_correctly(self, mock_session, mock_redis):
        """Bharati station_id is accepted by Bharati IngestionService."""
        from edge.ingestion.service import IngestionService

        with patch("edge.ingestion.service.get_redis", return_value=mock_redis):
            svc = IngestionService(session=mock_session, station_id="bharati")
            readings = [make_sensor_reading(station_id="bharati", sensor_id="bharati.energy.gen1.fuel_pct")]
            count = await svc.ingest(_make_batch(readings, station_id="bharati"))

        assert count == 1


class TestIngestionRouter:
    """Scenario 01B — /ingest HTTP endpoint schema validation."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from edge.ingestion.router import router
        from unittest.mock import AsyncMock, MagicMock

        app = FastAPI()
        app.include_router(router)

        async def mock_session_gen():
            yield AsyncMock()

        # Override dependencies
        from edge.deps import get_db_session, get_station_id
        app.dependency_overrides[get_db_session] = mock_session_gen
        app.dependency_overrides[get_station_id] = lambda: "maitri"

        with patch("edge.ingestion.service.get_redis", return_value=MagicMock(
            publish=AsyncMock(return_value=1)
        )):
            yield TestClient(app)

    def test_ingest_with_missing_body_returns_422(self, client):
        resp = client.post("/ingest", json={})
        assert resp.status_code == 422

    def test_ingest_content_type_required(self, client):
        resp = client.post("/ingest", data="not json", headers={"Content-Type": "text/plain"})
        assert resp.status_code in (415, 422)

    def test_ingest_endpoint_exists(self, client):
        """Verify the /ingest route is registered."""
        from fastapi import FastAPI
        from edge.ingestion.router import router
        app = FastAPI()
        app.include_router(router)
        paths = [r.path for r in app.routes]
        assert "/ingest" in paths
