"""Unit tests for Phase 5 — HQ Dashboard API.

Tests cover API router route registration, schema validation,
pagination logic, and health endpoint — all without a live DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from cloud.api.schemas import (
    AlertOut,
    AlertAcknowledgeIn,
    AnalyticsOut,
    DashboardSummaryOut,
    PaginatedResponse,
    SensorSummaryOut,
    StationConnectionOut,
)
from cloud.api.router import router as hq_router
from shared.utils.time import utcnow


# ---------------------------------------------------------------------------
# Test app — health route only (no DB needed)
# ---------------------------------------------------------------------------

import os
os.environ.setdefault("CLOUD_JWT_SECRET", "test-secret-phase5-only")

@pytest.fixture(scope="module")
def app():
    application = FastAPI()
    # Override JWT auth dependency so route-registration tests don't need real tokens
    from cloud.auth.deps import get_current_user
    application.dependency_overrides[get_current_user] = lambda: {"sub": "test-uid", "roles": ["ADMIN"]}
    application.include_router(hq_router)
    return application


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

class TestHQRouterRegistration:
    def test_health_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/health" in paths

    def test_dashboard_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/dashboard" in paths

    def test_stations_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/stations" in paths

    def test_alerts_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/alerts" in paths

    def test_single_alert_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/alerts/{alert_id}" in paths

    def test_acknowledge_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/alerts/{alert_id}/acknowledge" in paths

    def test_sensors_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/stations/{station_id}/sensors" in paths

    def test_analytics_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/stations/{station_id}/analytics" in paths

    def test_station_status_route_registered(self, app):
        paths = [r.path for r in app.routes]
        assert "/api/v1/hq/stations/{station_id}/status" in paths

    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/hq/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestAlertOutSchema:
    def _make_alert(self, resolved_at=None, triggered_offset_s=-300):
        now = utcnow()
        return AlertOut(
            alert_id="maitri-energy-111-aabb",
            station_id="maitri",
            severity="CRITICAL",
            domain="energy",
            asset_id="maitri.gen1",
            triggered_at=now + timedelta(seconds=triggered_offset_s),
            description="Fuel critically low",
            ack_state="OPEN",
            acknowledged_by=None,
            acknowledged_at=None,
            resolved_at=resolved_at,
            black_box_activated=True,
            synced_to_cloud=True,
        )

    def test_unresolved_duration_positive(self):
        a = self._make_alert()
        assert a.duration_open_s > 0

    def test_resolved_duration_matches_window(self):
        now = utcnow()
        triggered = now - timedelta(minutes=10)
        resolved = now - timedelta(minutes=5)
        a = AlertOut(
            alert_id="x",
            station_id="maitri",
            severity="HIGH",
            domain="weather",
            asset_id=None,
            triggered_at=triggered,
            description="test",
            ack_state="RESOLVED",
            acknowledged_by="ops",
            acknowledged_at=triggered,
            resolved_at=resolved,
            black_box_activated=False,
            synced_to_cloud=True,
        )
        assert abs(a.duration_open_s - 300.0) < 2.0

    def test_critical_severity_preserved(self):
        a = self._make_alert()
        assert a.severity == "CRITICAL"

    def test_black_box_flag_preserved(self):
        a = self._make_alert()
        assert a.black_box_activated is True


class TestStationConnectionOutSchema:
    def test_up_state(self):
        s = StationConnectionOut(
            station_id="maitri",
            display_name="Maitri Research Station",
            link_state="UP",
            last_heartbeat_at=utcnow(),
            queue_depth_bytes=1024,
            open_critical_alerts=0,
            open_high_alerts=1,
            services_healthy=True,
            minutes_since_heartbeat=0.5,
        )
        assert s.link_state == "UP"
        assert s.services_healthy is True

    def test_down_state_all_nulls(self):
        s = StationConnectionOut(
            station_id="bharati",
            display_name="Bharati Research Station",
            link_state="DOWN",
            last_heartbeat_at=None,
            queue_depth_bytes=None,
            open_critical_alerts=None,
            open_high_alerts=None,
            services_healthy=None,
            minutes_since_heartbeat=None,
        )
        assert s.last_heartbeat_at is None
        assert s.link_state == "DOWN"


class TestAnalyticsOutSchema:
    def test_alert_counts_dict(self):
        a = AnalyticsOut(
            station_id="maitri",
            period_hours=24.0,
            alert_counts_by_severity={"CRITICAL": 3, "HIGH": 5, "MEDIUM": 10, "LOW": 2},
            total_readings=28800,
            avg_readings_per_hour=1200.0,
            open_alerts_total=15,
        )
        assert sum(a.alert_counts_by_severity.values()) == 20
        assert a.open_alerts_total == 15


class TestPaginatedResponse:
    def test_structure(self):
        r = PaginatedResponse(total=100, page=2, page_size=20, items=["a", "b"])
        assert r.total == 100
        assert r.page == 2
        assert r.page_size == 20
        assert len(r.items) == 2

    def test_empty_items(self):
        r = PaginatedResponse(total=0, page=1, page_size=20, items=[])
        assert r.items == []
        assert r.total == 0


class TestAlertAcknowledgeIn:
    def test_requires_acknowledged_by(self):
        a = AlertAcknowledgeIn(acknowledged_by="dr.raghavan@ncpor.in")
        assert a.acknowledged_by == "dr.raghavan@ncpor.in"


class TestSensorSummaryOut:
    def test_fields(self):
        s = SensorSummaryOut(
            station_id="maitri",
            sensor_id="maitri.energy.gen1.fuel_pct",
            domain="energy",
            latest_value=45.3,
            latest_unit="pct",
            latest_ts=utcnow(),
            readings_count_24h=288,
        )
        assert s.domain == "energy"
        assert s.readings_count_24h == 288
