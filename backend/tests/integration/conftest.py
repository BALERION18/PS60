"""Shared fixtures for VajraX integration tests.

Integration tests exercise multiple components together using:
  - AsyncMock for DB sessions and Redis
  - In-process FastAPI TestClient for API endpoints
  - Real business logic (no mocking of domain code)

Design rule: never import edge.* and cloud.* in the same test module —
they are separate processes in production. Each scenario lives in its own
process-scoped namespace.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("CLOUD_JWT_SECRET", "inttest-secret-vajrax-2026")
os.environ.setdefault("STATION_ID", "maitri")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


# ---------------------------------------------------------------------------
# Shared test data factories
# ---------------------------------------------------------------------------

def make_sensor_reading(
    sensor_id: str = "maitri.energy.gen1.fuel_pct",
    station_id: str = "maitri",
    value: float = 45.3,
    domain: str = "energy",
    unit: str = "pct",
    quality_flag: str = "NOMINAL",
    offset_seconds: int = 0,
) -> dict:
    now = datetime.now(tz=timezone.utc) - timedelta(seconds=offset_seconds)
    return {
        "sensor_id": sensor_id,
        "station_id": station_id,
        "value": value,
        "domain": domain,
        "unit": unit,
        "quality_flag": quality_flag,
        "timestamp_utc": now.isoformat(),
        "asset_id": f"{station_id}.gen1",
        "metric_name": "fuel_level_percent",
        "raw_payload": {"v": value},
    }


def make_alert(
    alert_id: str | None = None,
    station_id: str = "maitri",
    severity: str = "CRITICAL",
    domain: str = "energy",
    ack_state: str = "OPEN",
    synced_to_cloud: bool = True,
) -> dict:
    return {
        "alert_id": alert_id or f"{station_id}-energy-{uuid.uuid4().hex[:8]}-aabb",
        "station_id": station_id,
        "severity": severity,
        "domain": domain,
        "asset_id": f"{station_id}.gen1",
        "description": f"Test alert [{severity}]",
        "ack_state": ack_state,
        "triggered_at": datetime.now(tz=timezone.utc).isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "resolved_at": None,
        "black_box_activated": severity == "CRITICAL",
        "synced_to_cloud": synced_to_cloud,
    }


def make_jwt_token(roles: list[str] = None, user_id: str = "test-uid") -> str:
    from cloud.auth.jwt_handler import create_access_token
    return create_access_token(user_id, "test-user@ncpor.in", roles or ["OPERATOR"])


# ---------------------------------------------------------------------------
# Mock DB session factory
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """An AsyncMock that behaves like an AsyncSession for integration tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """An AsyncMock that behaves like a Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.publish = AsyncMock(return_value=1)
    r.setex = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    r.delete = AsyncMock(return_value=1)
    r.zadd = AsyncMock(return_value=1)
    r.zpopmin = AsyncMock(return_value=[])
    r.zcard = AsyncMock(return_value=0)
    return r
