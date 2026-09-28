"""Integration Scenario 03 — Edge-to-Cloud Sync Pipeline.

Tests the complete sync envelope pipeline with the real API:
  - build_envelope() → unpack_envelope() roundtrip
  - Signature tamper detection
  - Wrong-station key rejection
  - Wire size within 64KB satellite MTU
  - zstd compression ratio
  - MQTT topic helpers
  - Queue priority ordering
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.crypto.signing import generate_station_keypair, Signer, Verifier
from edge.sync_agent.envelope import build_envelope, unpack_envelope, envelope_wire_size
from edge.sync_agent.queue_manager import MESSAGE_PRIORITY
from edge.sync_agent.mqtt_client import sync_topic, heartbeat_topic, downlink_topic


# ---------------------------------------------------------------------------
# Scenario 03A — Envelope round-trip (real Ed25519 keypairs)
# ---------------------------------------------------------------------------

class TestSyncEnvelopeRoundTrip:

    @pytest.fixture(scope="class")
    def maitri_keys(self):
        priv, pub = generate_station_keypair()
        return Signer.from_pem_bytes(priv), Verifier.from_pem_bytes(pub)

    @pytest.fixture(scope="class")
    def bharati_keys(self):
        priv, pub = generate_station_keypair()
        return Signer.from_pem_bytes(priv), Verifier.from_pem_bytes(pub)

    def test_sensor_batch_roundtrip(self, maitri_keys):
        signer, verifier = maitri_keys
        payload = {"readings": [{"sensor_id": "maitri.energy.gen1.fuel_pct", "value": 42.0}]}
        env = build_envelope("maitri", "SENSOR_BATCH", payload, 1, signer)
        unpacked = unpack_envelope(env, verifier=verifier)
        assert unpacked["readings"][0]["value"] == 42.0

    def test_alert_critical_roundtrip(self, maitri_keys):
        signer, verifier = maitri_keys
        payload = {"alert_id": "maitri-energy-001-aabb", "severity": "CRITICAL"}
        env = build_envelope("maitri", "ALERT_CRITICAL", payload, 2, signer)
        unpacked = unpack_envelope(env, verifier=verifier)
        assert unpacked["severity"] == "CRITICAL"

    def test_envelope_has_required_fields(self, maitri_keys):
        signer, _ = maitri_keys
        env = build_envelope("maitri", "SENSOR_BATCH", {"readings": []}, 3, signer)
        for field in ("station_id", "message_type", "sequence_number",
                      "compressed_payload", "signature", "timestamp_utc",
                      "payload_size_bytes", "compressed_size_bytes"):
            assert field in env, f"Missing envelope field: {field}"

    def test_tampered_payload_rejected(self, maitri_keys):
        from shared.crypto.signing import VerificationError
        signer, verifier = maitri_keys
        env = build_envelope("maitri", "SENSOR_BATCH", {"readings": []}, 4, signer)
        env["compressed_payload"] = env["compressed_payload"][:-4] + "XXXX"
        with pytest.raises(Exception):  # VerificationError or ZstdError
            unpack_envelope(env, verifier=verifier)

    def test_wrong_station_key_rejected(self, maitri_keys, bharati_keys):
        from shared.crypto.signing import VerificationError
        maitri_signer, _ = maitri_keys
        _, bharati_verifier = bharati_keys
        env = build_envelope("maitri", "SENSOR_BATCH", {"readings": []}, 5, maitri_signer)
        with pytest.raises(Exception):
            unpack_envelope(env, verifier=bharati_verifier)

    def test_wire_size_under_64kb_for_100_readings(self, maitri_keys):
        signer, _ = maitri_keys
        payload = {
            "readings": [
                {"sensor_id": f"maitri.energy.s{i}", "value": float(i), "ts": "2026-01-01T00:00:00Z"}
                for i in range(100)
            ]
        }
        env = build_envelope("maitri", "SENSOR_BATCH", payload, 6, signer)
        wire_bytes = envelope_wire_size(env)
        assert wire_bytes < 65536, f"Wire size {wire_bytes} bytes > 64KB satellite MTU"

    def test_zstd_compression_better_than_50pct(self, maitri_keys):
        signer, _ = maitri_keys
        payload = {
            "readings": [
                {"sensor_id": "maitri.energy.gen1.fuel_pct", "value": float(i), "unit": "pct",
                 "quality_flag": "NOMINAL", "timestamp_utc": "2026-01-01T00:00:00Z"}
                for i in range(100)
            ]
        }
        json_size = len(json.dumps(payload).encode())
        env = build_envelope("maitri", "SENSOR_BATCH", payload, 7, signer)
        ratio = env["compressed_size_bytes"] / json_size
        assert ratio <= 0.5, f"Compression ratio {ratio:.2%} worse than 50%"

    def test_sequence_number_stored(self, maitri_keys):
        signer, _ = maitri_keys
        env = build_envelope("maitri", "SENSOR_BATCH", {"x": 1}, 99, signer)
        assert env["sequence_number"] == 99

    def test_station_id_stored_in_envelope(self, maitri_keys):
        signer, _ = maitri_keys
        env = build_envelope("bharati", "SENSOR_BATCH", {"x": 1}, 1, signer)
        assert env["station_id"] == "bharati"


# ---------------------------------------------------------------------------
# Scenario 03B — MQTT topic helpers
# ---------------------------------------------------------------------------

class TestMQTTTopicHelpers:

    def test_sync_topic_maitri_sensor(self):
        assert sync_topic("maitri", "SENSOR_BATCH") == "dt/maitri/sync/sensor_batch"

    def test_sync_topic_bharati_critical(self):
        assert sync_topic("bharati", "ALERT_CRITICAL") == "dt/bharati/sync/alert_critical"

    def test_heartbeat_topic_maitri(self):
        assert heartbeat_topic("maitri") == "dt/maitri/heartbeat"

    def test_heartbeat_topic_bharati(self):
        assert heartbeat_topic("bharati") == "dt/bharati/heartbeat"

    def test_downlink_topic_maitri(self):
        assert downlink_topic("maitri") == "cmd/maitri/#"

    def test_station_id_parsed_from_sync_topic(self):
        topic = "dt/maitri/sync/sensor_batch"
        assert topic.split("/")[1] == "maitri"

    def test_station_id_parsed_from_heartbeat_topic(self):
        topic = "dt/bharati/heartbeat"
        assert topic.split("/")[1] == "bharati"

    def test_message_type_lowercase_in_topic(self):
        topic = sync_topic("maitri", "ALERT_CRITICAL")
        assert "alert_critical" in topic
        assert "ALERT_CRITICAL" not in topic


# ---------------------------------------------------------------------------
# Scenario 03C — Queue priority ordering
# ---------------------------------------------------------------------------

class TestQueuePriorityOrdering:

    def test_black_box_is_priority_zero(self):
        assert MESSAGE_PRIORITY["BLACK_BOX_FRAME"] == 0

    def test_critical_before_telemetry(self):
        assert MESSAGE_PRIORITY["ALERT_CRITICAL"] < MESSAGE_PRIORITY["SENSOR_BATCH"]

    def test_critical_and_high_equal(self):
        assert MESSAGE_PRIORITY["ALERT_CRITICAL"] == MESSAGE_PRIORITY["ALERT_HIGH"]

    def test_heartbeat_above_critical(self):
        assert MESSAGE_PRIORITY["LINK_HEARTBEAT"] > MESSAGE_PRIORITY["ALERT_CRITICAL"]

    def test_inventory_lowest_or_equal_telemetry(self):
        assert MESSAGE_PRIORITY["INVENTORY_SNAPSHOT"] >= MESSAGE_PRIORITY["SENSOR_BATCH"]

    def test_full_priority_chain_sorted(self):
        ordered = [
            "BLACK_BOX_FRAME",
            "ALERT_CRITICAL",
            "ALERT_HIGH",
            "ALERT_MEDIUM",
            "ALERT_LOW",
            "LINK_HEARTBEAT",
            "SENSOR_BATCH",
        ]
        scores = [MESSAGE_PRIORITY[m] for m in ordered]
        assert scores == sorted(scores), "Priority chain order is violated"
