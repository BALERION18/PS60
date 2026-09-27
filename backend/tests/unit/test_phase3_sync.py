"""Unit tests for Phase 3 — Satellite Sync Agent.

All tests are pure-function and require no external services (no Redis,
no MQTT, no DB). Cryptographic tests use in-memory generated keypairs.
"""
from __future__ import annotations

import base64
import json

import pytest

from shared.crypto.signing import Signer, VerificationError, Verifier, generate_station_keypair
from edge.sync_agent.envelope import build_envelope, envelope_wire_size, unpack_envelope
from edge.sync_agent.queue_manager import MESSAGE_PRIORITY, _score
from edge.sync_agent.mqtt_client import (
    QOS_CRITICAL,
    QOS_TELEMETRY,
    downlink_topic,
    heartbeat_topic,
    sync_topic,
)


# ---------------------------------------------------------------------------
# Fixtures — generate a throwaway Ed25519 keypair for testing
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def keypair():
    priv_pem, pub_pem = generate_station_keypair()
    return Signer.from_pem_bytes(priv_pem), Verifier.from_pem_bytes(pub_pem)


@pytest.fixture(scope="module")
def signer(keypair):
    return keypair[0]


@pytest.fixture(scope="module")
def verifier(keypair):
    return keypair[1]


@pytest.fixture
def sample_payload():
    return {
        "station_id": "maitri",
        "readings": [
            {"sensor_id": "maitri.energy.gen1.fuel_pct", "value": 72.5, "unit": "pct"},
            {"sensor_id": "maitri.weather.aws.wind_speed_ms", "value": 12.3, "unit": "m/s"},
        ],
        "batch_id": "test-batch-001",
    }


# ---------------------------------------------------------------------------
# Envelope — build_envelope
# ---------------------------------------------------------------------------

class TestBuildEnvelope:
    def test_returns_dict_with_required_keys(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        for key in ("station_id", "message_type", "sequence_number",
                    "compressed_payload", "signature", "timestamp_utc",
                    "payload_size_bytes", "compressed_size_bytes"):
            assert key in env, f"Missing key: {key}"

    def test_station_id_preserved(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 42, signer)
        assert env["station_id"] == "maitri"

    def test_message_type_preserved(self, signer, sample_payload):
        env = build_envelope("maitri", "ALERT_CRITICAL", sample_payload, 1, signer)
        assert env["message_type"] == "ALERT_CRITICAL"

    def test_sequence_number_preserved(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 99, signer)
        assert env["sequence_number"] == 99

    def test_compressed_payload_is_base64(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        # Should decode without error
        decoded = base64.b64decode(env["compressed_payload"])
        assert len(decoded) > 0

    def test_signature_is_64_bytes(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        sig_bytes = base64.b64decode(env["signature"])
        assert len(sig_bytes) == 64

    def test_compression_reduces_size(self, signer):
        # Large repetitive payload should compress well
        large_payload = {"data": "a" * 5000}
        env = build_envelope("maitri", "SENSOR_BATCH", large_payload, 1, signer)
        assert env["compressed_size_bytes"] < env["payload_size_bytes"]

    def test_envelope_is_json_serializable(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        dumped = json.dumps(env)
        assert isinstance(dumped, str) and len(dumped) > 0


# ---------------------------------------------------------------------------
# Envelope — unpack_envelope (roundtrip)
# ---------------------------------------------------------------------------

class TestUnpackEnvelope:
    def test_roundtrip_exact_payload(self, signer, verifier, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        recovered = unpack_envelope(env, verifier)
        assert recovered == sample_payload

    def test_roundtrip_empty_payload(self, signer, verifier):
        env = build_envelope("maitri", "LINK_HEARTBEAT", {}, 1, signer)
        assert unpack_envelope(env, verifier) == {}

    def test_roundtrip_nested_payload(self, signer, verifier):
        nested = {"a": {"b": {"c": [1, 2, 3]}}}
        env = build_envelope("bharati", "ALERT_CRITICAL", nested, 5, signer)
        assert unpack_envelope(env, verifier) == nested

    def test_tampered_signature_raises(self, signer, verifier, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        # Flip one byte in the signature
        sig_bytes = bytearray(base64.b64decode(env["signature"]))
        sig_bytes[0] ^= 0xFF
        env["signature"] = base64.b64encode(bytes(sig_bytes)).decode("ascii")
        with pytest.raises(VerificationError):
            unpack_envelope(env, verifier)

    def test_tampered_payload_raises(self, signer, verifier, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        # Corrupt the compressed payload bytes
        comp_bytes = bytearray(base64.b64decode(env["compressed_payload"]))
        comp_bytes[-1] ^= 0xFF
        env["compressed_payload"] = base64.b64encode(bytes(comp_bytes)).decode("ascii")
        with pytest.raises(Exception):  # VerificationError or ZstdError
            unpack_envelope(env, verifier)

    def test_wrong_station_key_raises(self, signer, sample_payload):
        """Verify with a different key should fail."""
        _, other_pub = generate_station_keypair()
        other_verifier = Verifier.from_pem_bytes(other_pub)
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        with pytest.raises(VerificationError):
            unpack_envelope(env, other_verifier)


# ---------------------------------------------------------------------------
# Envelope wire size helper
# ---------------------------------------------------------------------------

class TestEnvelopeWireSize:
    def test_returns_positive_int(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        assert envelope_wire_size(env) > 0

    def test_includes_overhead(self, signer, sample_payload):
        env = build_envelope("maitri", "SENSOR_BATCH", sample_payload, 1, signer)
        assert envelope_wire_size(env) > env["compressed_size_bytes"]


# ---------------------------------------------------------------------------
# Queue manager — MESSAGE_PRIORITY dict
# ---------------------------------------------------------------------------

class TestMessagePriority:
    def test_black_box_frame_is_priority_zero(self):
        assert MESSAGE_PRIORITY["BLACK_BOX_FRAME"] == 0

    def test_alert_critical_is_priority_one(self):
        assert MESSAGE_PRIORITY["ALERT_CRITICAL"] == 1

    def test_alert_high_is_priority_one(self):
        assert MESSAGE_PRIORITY["ALERT_HIGH"] == 1

    def test_alert_medium_is_priority_two(self):
        assert MESSAGE_PRIORITY["ALERT_MEDIUM"] == 2

    def test_alert_low_is_priority_two(self):
        assert MESSAGE_PRIORITY["ALERT_LOW"] == 2

    def test_sensor_batch_is_priority_three(self):
        assert MESSAGE_PRIORITY["SENSOR_BATCH"] == 3

    def test_inventory_snapshot_is_priority_three(self):
        assert MESSAGE_PRIORITY["INVENTORY_SNAPSHOT"] == 3

    def test_link_heartbeat_is_priority_two(self):
        assert MESSAGE_PRIORITY["LINK_HEARTBEAT"] == 2


# ---------------------------------------------------------------------------
# Queue manager — _score sorting
# ---------------------------------------------------------------------------

class TestQueueScore:
    def test_lower_priority_has_lower_score(self):
        """Priority 0 should produce a lower score than priority 3 at same time."""
        score_p0 = _score(0, 1000)
        score_p3 = _score(3, 1000)
        assert score_p0 < score_p3

    def test_same_priority_ordered_by_time(self):
        """Earlier creation time = lower score = dequeued first."""
        early = _score(1, 1000)
        late = _score(1, 2000)
        assert early < late

    def test_higher_priority_beats_earlier_time(self):
        """Priority 0 at t=2000 still beats priority 3 at t=1000."""
        p0_late = _score(0, 2000)
        p3_early = _score(3, 1000)
        assert p0_late < p3_early

    def test_score_is_float(self):
        assert isinstance(_score(0, 1000), float)


# ---------------------------------------------------------------------------
# MQTT client — topic helpers
# ---------------------------------------------------------------------------

class TestMQTTTopicHelpers:
    def test_sync_topic_format(self):
        assert sync_topic("maitri", "SENSOR_BATCH") == "dt/maitri/sync/sensor_batch"

    def test_sync_topic_lowercases_message_type(self):
        assert sync_topic("bharati", "ALERT_CRITICAL") == "dt/bharati/sync/alert_critical"

    def test_heartbeat_topic_format(self):
        assert heartbeat_topic("maitri") == "dt/maitri/heartbeat"

    def test_heartbeat_topic_bharati(self):
        assert heartbeat_topic("bharati") == "dt/bharati/heartbeat"

    def test_downlink_topic_format(self):
        assert downlink_topic("maitri") == "cmd/maitri/#"

    def test_qos_critical_is_two(self):
        assert QOS_CRITICAL == 2

    def test_qos_telemetry_is_one(self):
        assert QOS_TELEMETRY == 1

    def test_sync_topics_differ_by_station(self):
        m = sync_topic("maitri", "SENSOR_BATCH")
        b = sync_topic("bharati", "SENSOR_BATCH")
        assert m != b
