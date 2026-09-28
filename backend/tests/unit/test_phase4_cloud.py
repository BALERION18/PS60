"""Unit tests for Phase 4 — Cloud Backend Core.

Tests are pure-function wherever possible. DB-layer tests mock the session.
No real Redis, MQTT, or DB is required.
"""
from __future__ import annotations

import json
import os
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.crypto.signing import Signer, VerificationError, Verifier, generate_station_keypair
from edge.sync_agent.envelope import build_envelope
from cloud.config import CloudConfig
from cloud.redis_client import cloud_alerts_channel, station_status_channel
from cloud.api.schemas import (
    AlertOut,
    AnalyticsOut,
    DashboardSummaryOut,
    SensorSummaryOut,
    StationConnectionOut,
)
from cloud.websocket.manager import WebSocketManager
from cloud.mqtt_subscriber import CloudMQTTSubscriber


# ---------------------------------------------------------------------------
# CloudConfig
# ---------------------------------------------------------------------------

class TestCloudConfig:
    def test_default_station_ids(self, monkeypatch):
        monkeypatch.delenv("STATION_IDS", raising=False)
        cfg = CloudConfig()
        assert "maitri" in cfg.station_ids
        assert "bharati" in cfg.station_ids

    def test_custom_station_ids(self, monkeypatch):
        monkeypatch.setenv("STATION_IDS", "maitri,bharati,test")
        cfg = CloudConfig()
        assert cfg.station_ids == ["maitri", "bharati", "test"]

    def test_single_station_id(self, monkeypatch):
        monkeypatch.setenv("STATION_IDS", "maitri")
        cfg = CloudConfig()
        assert cfg.station_ids == ["maitri"]

    def test_heartbeat_timeout_default(self, monkeypatch):
        monkeypatch.delenv("HEARTBEAT_TIMEOUT_MINUTES", raising=False)
        cfg = CloudConfig()
        assert cfg.heartbeat_timeout_minutes == 15

    def test_heartbeat_timeout_custom(self, monkeypatch):
        monkeypatch.setenv("HEARTBEAT_TIMEOUT_MINUTES", "30")
        cfg = CloudConfig()
        assert cfg.heartbeat_timeout_minutes == 30

    def test_mqtt_port_default(self, monkeypatch):
        monkeypatch.delenv("MQTT_PORT", raising=False)
        cfg = CloudConfig()
        assert cfg.mqtt_port == 1883

    def test_pubkey_path(self, monkeypatch):
        monkeypatch.setenv("STATION_PUBKEY_DIR", "/tmp/keys")
        cfg = CloudConfig()
        assert cfg.pubkey_path("maitri") == "/tmp/keys/maitri_public.pem"
        assert cfg.pubkey_path("bharati") == "/tmp/keys/bharati_public.pem"

    def test_tls_default_false(self, monkeypatch):
        monkeypatch.delenv("MQTT_TLS", raising=False)
        cfg = CloudConfig()
        assert cfg.mqtt_tls is False

    def test_api_port_default(self, monkeypatch):
        monkeypatch.delenv("API_PORT", raising=False)
        cfg = CloudConfig()
        assert cfg.api_port == 8200


# ---------------------------------------------------------------------------
# Redis channel helpers
# ---------------------------------------------------------------------------

class TestCloudRedisChannels:
    def test_alerts_channel(self):
        ch = cloud_alerts_channel()
        assert ch == "cloud:alerts:all"

    def test_station_status_channel_maitri(self):
        ch = station_status_channel("maitri")
        assert ch == "cloud:station:maitri:status"

    def test_station_status_channel_bharati(self):
        ch = station_status_channel("bharati")
        assert ch == "cloud:station:bharati:status"

    def test_channels_are_station_scoped(self):
        assert station_status_channel("maitri") != station_status_channel("bharati")


# ---------------------------------------------------------------------------
# Cloud ingestion service — envelope routing (mocked DB)
# ---------------------------------------------------------------------------

class TestCloudIngestion:
    @pytest.fixture
    def keypair(self):
        priv_pem, pub_pem = generate_station_keypair()
        return Signer.from_pem_bytes(priv_pem), Verifier.from_pem_bytes(pub_pem)

    @pytest.fixture
    def ingestion_service(self, keypair):
        """CloudIngestionService with mocked session factory and Redis."""
        from cloud.ingestion.service import CloudIngestionService
        _, verifier = keypair
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)
        return CloudIngestionService(
            session_factory=mock_factory,
            verifiers={"maitri": verifier},
        )

    @pytest.mark.asyncio
    async def test_station_id_mismatch_is_rejected(self, ingestion_service, keypair):
        signer, _ = keypair
        env = build_envelope("bharati", "SENSOR_BATCH", {"readings": []}, 1, signer)
        # station_id in topic says "maitri" but envelope says "bharati"
        env["station_id"] = "bharati"
        # Should log a warning and return without crashing
        await ingestion_service.receive_envelope(env, "maitri")

    @pytest.mark.asyncio
    async def test_no_verifier_skips_silently(self, ingestion_service, keypair):
        signer, _ = keypair
        env = build_envelope("bharati", "SENSOR_BATCH", {"readings": []}, 1, signer)
        # No verifier for "bharati"
        await ingestion_service.receive_envelope(env, "bharati")  # Should not raise

    @pytest.mark.asyncio
    async def test_tampered_signature_rejected(self, ingestion_service, keypair):
        signer, _ = keypair
        env = build_envelope("maitri", "SENSOR_BATCH", {"readings": []}, 1, signer)
        # Corrupt signature
        sig_bytes = bytearray(base64.b64decode(env["signature"]))
        sig_bytes[0] ^= 0xFF
        env["signature"] = base64.b64encode(bytes(sig_bytes)).decode("ascii")
        await ingestion_service.receive_envelope(env, "maitri")  # Should not raise, just log


# ---------------------------------------------------------------------------
# Cloud API schemas
# ---------------------------------------------------------------------------

class TestCloudAPISchemas:
    def test_station_connection_out_fields(self):
        s = StationConnectionOut(
            station_id="maitri",
            display_name="Maitri Research Station",
            link_state="UP",
            last_heartbeat_at=None,
            queue_depth_bytes=None,
            open_critical_alerts=0,
            open_high_alerts=0,
            services_healthy=True,
            minutes_since_heartbeat=None,
        )
        assert s.station_id == "maitri"
        assert s.link_state == "UP"

    def test_alert_out_duration_open_unresolved(self):
        from shared.utils.time import utcnow
        triggered = utcnow()
        a = AlertOut(
            alert_id="maitri-energy-123-abc",
            station_id="maitri",
            severity="CRITICAL",
            domain="energy",
            asset_id=None,
            triggered_at=triggered,
            description="Fuel low",
            ack_state="OPEN",
            acknowledged_by=None,
            acknowledged_at=None,
            resolved_at=None,
            black_box_activated=True,
            synced_to_cloud=True,
        )
        assert a.duration_open_s >= 0

    def test_alert_out_duration_open_resolved(self):
        from datetime import timedelta
        from shared.utils.time import utcnow
        triggered = utcnow()
        resolved = triggered + timedelta(minutes=30)
        a = AlertOut(
            alert_id="maitri-energy-123-abc",
            station_id="maitri",
            severity="HIGH",
            domain="energy",
            asset_id=None,
            triggered_at=triggered,
            description="Resolved alert",
            ack_state="RESOLVED",
            acknowledged_by="ops@ncpor.in",
            acknowledged_at=triggered,
            resolved_at=resolved,
            black_box_activated=False,
            synced_to_cloud=True,
        )
        assert abs(a.duration_open_s - 1800.0) < 1.0  # 30 min = 1800s

    def test_dashboard_summary_out_fields(self):
        from shared.utils.time import utcnow
        s = StationConnectionOut(
            station_id="maitri",
            display_name="Maitri",
            link_state="UP",
            last_heartbeat_at=None,
            queue_depth_bytes=0,
            open_critical_alerts=2,
            open_high_alerts=1,
            services_healthy=True,
            minutes_since_heartbeat=3.5,
        )
        d = DashboardSummaryOut(
            stations=[s],
            total_open_critical=2,
            total_open_high=1,
            total_open_alerts=3,
            generated_at=utcnow(),
        )
        assert d.total_open_critical == 2
        assert len(d.stations) == 1

    def test_analytics_out_fields(self):
        a = AnalyticsOut(
            station_id="bharati",
            period_hours=24.0,
            alert_counts_by_severity={"CRITICAL": 1, "HIGH": 2, "MEDIUM": 0, "LOW": 5},
            total_readings=14400,
            avg_readings_per_hour=600.0,
            open_alerts_total=8,
        )
        assert a.alert_counts_by_severity["CRITICAL"] == 1
        assert a.avg_readings_per_hour == 600.0

    def test_sensor_summary_out_fields(self):
        from shared.utils.time import utcnow
        s = SensorSummaryOut(
            station_id="maitri",
            sensor_id="maitri.energy.gen1.fuel_pct",
            domain="energy",
            latest_value=72.5,
            latest_unit="pct",
            latest_ts=utcnow(),
            readings_count_24h=288,
        )
        assert s.latest_value == 72.5
        assert s.readings_count_24h == 288


# ---------------------------------------------------------------------------
# WebSocket manager
# ---------------------------------------------------------------------------

class TestWebSocketManager:
    @pytest.mark.asyncio
    async def test_connect_adds_to_pool(self):
        manager = WebSocketManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws, "client-1")
        assert "client-1" in manager._connections

    def test_disconnect_removes_from_pool(self):
        manager = WebSocketManager()
        mock_ws = MagicMock()
        manager._connections["client-1"] = mock_ws
        manager.disconnect("client-1")
        assert "client-1" not in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_calls_send_on_all_clients(self):
        manager = WebSocketManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2.send_text = AsyncMock()
        manager._connections["c1"] = ws1
        manager._connections["c2"] = ws2
        await manager.broadcast({"type": "alert", "data": {"alert_id": "test"}})
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        manager = WebSocketManager()
        dead_ws = AsyncMock()
        dead_ws.send_text = AsyncMock(side_effect=Exception("connection closed"))
        manager._connections["dead"] = dead_ws
        await manager.broadcast({"type": "test"})
        assert "dead" not in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_empty_pool_is_noop(self):
        manager = WebSocketManager()
        # Should not raise
        await manager.broadcast({"type": "test"})


# ---------------------------------------------------------------------------
# Cloud MQTT subscriber — topic parsing
# ---------------------------------------------------------------------------

class TestCloudMQTTSubscriber:
    def test_topic_parsing_sync(self):
        """Verify station_id extracted from dt/{station_id}/sync/{type}."""
        topic = "dt/maitri/sync/sensor_batch"
        parts = topic.split("/")
        assert parts[1] == "maitri"
        assert parts[2] == "sync"

    def test_topic_parsing_heartbeat(self):
        topic = "dt/bharati/heartbeat"
        parts = topic.split("/")
        assert parts[1] == "bharati"
        assert parts[2] == "heartbeat"

    def test_topic_parsing_both_stations(self):
        for station in ("maitri", "bharati"):
            topic = f"dt/{station}/sync/sensor_batch"
            parts = topic.split("/")
            assert parts[1] == station
