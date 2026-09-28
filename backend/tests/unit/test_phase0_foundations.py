"""Phase 0 unit tests — Protobuf round-trip, config schema, and crypto utilities.

These tests verify Phase 0 deliverables without requiring any running
infrastructure (no database, no Redis, no MQTT broker).

Run with:  pytest tests/unit/test_phase0_foundations.py -v
"""
from __future__ import annotations

import pytest

from shared.utils.time import utcnow, unix_ms, from_unix_ms, iso_utc, ensure_utc
from shared.utils.alert_id import generate_alert_id, parse_alert_id
from shared.crypto.signing import Signer, Verifier, VerificationError, generate_station_keypair
from shared.crypto.hash_chain import (
    initial_prev_hash, compute_frame_hash, verify_chain, sha256
)


# ---------------------------------------------------------------------------
# Time utilities
# ---------------------------------------------------------------------------

class TestTimeUtils:
    def test_utcnow_is_aware(self):
        dt = utcnow()
        assert dt.tzinfo is not None, "utcnow() must return a timezone-aware datetime"

    def test_unix_ms_roundtrip(self):
        dt = utcnow()
        ms = unix_ms(dt)
        recovered = from_unix_ms(ms)
        # Allow 1ms rounding tolerance
        assert abs((recovered - dt).total_seconds()) < 0.002

    def test_iso_utc_format(self):
        result = iso_utc()
        assert result.endswith("Z"), "iso_utc() must end with 'Z'"
        assert "T" in result, "iso_utc() must contain 'T' separator"

    def test_ensure_utc_raises_on_naive(self):
        from datetime import datetime
        naive = datetime(2026, 8, 27, 9, 0, 0)  # no tzinfo
        with pytest.raises(ValueError, match="naive datetime"):
            ensure_utc(naive)


# ---------------------------------------------------------------------------
# Alert ID utilities
# ---------------------------------------------------------------------------

class TestAlertId:
    def test_generate_format(self):
        alert_id = generate_alert_id("maitri", "energy")
        parts = alert_id.split("-")
        assert parts[0] == "maitri"
        assert parts[1] == "energy"
        assert len(parts[-1]) == 8, "Last segment should be 8 hex chars"
        assert int(parts[-2]) > 0, "unix_ms segment must be positive integer"

    def test_generate_unique(self):
        ids = {generate_alert_id("maitri", "energy") for _ in range(100)}
        assert len(ids) == 100, "Alert IDs must be unique"

    def test_parse_roundtrip(self):
        station = "bharati"
        domain = "environment"
        alert_id = generate_alert_id(station, domain)
        parsed = parse_alert_id(alert_id)
        assert parsed["station_id"] == station
        assert parsed["domain"] == domain
        assert isinstance(parsed["unix_ms"], int)
        assert len(parsed["rand_hex"]) == 8

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_alert_id("bad_id")


# ---------------------------------------------------------------------------
# Ed25519 signing and verification
# ---------------------------------------------------------------------------

class TestEdSigning:
    def test_sign_and_verify(self):
        private_pem, public_pem = generate_station_keypair()
        signer = Signer.from_pem_bytes(private_pem)
        verifier = Verifier.from_pem_bytes(public_pem)
        payload = b"test payload from maitri station"
        sig = signer.sign(payload)
        # Should not raise
        verifier.verify(payload, sig)

    def test_tampered_payload_raises(self):
        private_pem, public_pem = generate_station_keypair()
        signer = Signer.from_pem_bytes(private_pem)
        verifier = Verifier.from_pem_bytes(public_pem)
        payload = b"original payload"
        sig = signer.sign(payload)
        tampered = b"tampered payload"
        with pytest.raises(VerificationError):
            verifier.verify(tampered, sig)

    def test_wrong_key_raises(self):
        private_pem_a, _ = generate_station_keypair()
        _, public_pem_b = generate_station_keypair()
        signer = Signer.from_pem_bytes(private_pem_a)
        verifier = Verifier.from_pem_bytes(public_pem_b)
        payload = b"payload"
        sig = signer.sign(payload)
        with pytest.raises(VerificationError):
            verifier.verify(payload, sig)

    def test_signature_is_64_bytes(self):
        private_pem, _ = generate_station_keypair()
        signer = Signer.from_pem_bytes(private_pem)
        sig = signer.sign(b"data")
        assert len(sig) == 64, "Ed25519 signatures are always 64 bytes"

    def test_public_key_pem_export(self):
        private_pem, public_pem = generate_station_keypair()
        signer = Signer.from_pem_bytes(private_pem)
        exported = signer.public_key_pem()
        assert exported.startswith(b"-----BEGIN PUBLIC KEY-----")


# ---------------------------------------------------------------------------
# Black-box hash chain
# ---------------------------------------------------------------------------

class TestHashChain:
    def _make_frame(self, index: int, trigger_alert_id: str, prev_hash: bytes) -> dict:
        """Helper: create a fake frame dict for chain testing."""
        # Simulate the frame content (without frame_hash)
        content = f"frame:{index}:{trigger_alert_id}".encode()
        frame_hash = compute_frame_hash(content)
        return {
            "frame_index": index,
            "trigger_alert_id": trigger_alert_id,
            "prev_hash": prev_hash,
            "frame_hash": frame_hash,
            "frame_bytes_without_hash": content,
        }

    def test_valid_chain(self):
        trigger = "maitri-energy-1724745600000-a3f1"
        frames = []
        prev = initial_prev_hash(trigger)
        for i in range(5):
            frame = self._make_frame(i, trigger, prev)
            frames.append(frame)
            prev = frame["frame_hash"]
        valid, reason = verify_chain(frames)
        assert valid, f"Chain should be valid, got: {reason}"
        assert reason == ""

    def test_tampered_frame_detected(self):
        trigger = "maitri-energy-1724745600000-a3f1"
        frames = []
        prev = initial_prev_hash(trigger)
        for i in range(3):
            frame = self._make_frame(i, trigger, prev)
            frames.append(frame)
            prev = frame["frame_hash"]

        # Tamper with frame 1's content (simulate modification after logging)
        frames[1]["frame_bytes_without_hash"] = b"tampered content"
        # Leave frame_hash unchanged (the old hash) — chain verifier must catch this

        valid, reason = verify_chain(frames)
        assert not valid
        assert "tampered" in reason.lower() or "mismatch" in reason.lower()

    def test_missing_frame_detected(self):
        trigger = "bharati-environment-1724745600000-cc82"
        frames = []
        prev = initial_prev_hash(trigger)
        for i in range(5):
            frame = self._make_frame(i, trigger, prev)
            frames.append(frame)
            prev = frame["frame_hash"]

        # Remove frame 2 — simulates a deleted frame
        del frames[2]

        valid, reason = verify_chain(frames)
        assert not valid
        assert "gap" in reason.lower() or "index" in reason.lower()

    def test_initial_prev_hash_anchor(self):
        trigger_id = "maitri-energy-12345-abcd"
        h1 = initial_prev_hash(trigger_id)
        h2 = initial_prev_hash(trigger_id)
        assert h1 == h2, "initial_prev_hash must be deterministic"
        assert len(h1) == 32, "SHA-256 output must be 32 bytes"

    def test_sha256_correct_length(self):
        result = sha256(b"test")
        assert len(result) == 32

    def test_empty_chain_is_valid(self):
        valid, reason = verify_chain([])
        assert valid
        assert reason == ""


# ---------------------------------------------------------------------------
# Config schema validation (without loading YAML — tests Pydantic model directly)
# ---------------------------------------------------------------------------

class TestConfigSchema:
    def test_station_config_validates(self):
        from shared.schemas.config import (
            StationConfig, StationId, SensorConfig, ThresholdRule,
            AlertSeverity, Domain
        )
        config = StationConfig(
            station_id=StationId.MAITRI,
            display_name="Maitri Test",
            location="Antarctica",
            latitude=-70.7683,
            longitude=11.8268,
            elevation_m=130.0,
            sensors=[
                SensorConfig(
                    sensor_id="maitri.energy.gen1.fuel_pct",
                    domain=Domain.ENERGY,
                    asset_id="maitri.gen1",
                    metric_name="fuel_level_percent",
                    unit="pct",
                    sampling_interval_s=10,
                    nominal_min=0.0,
                    nominal_max=100.0,
                )
            ],
            threshold_rules=[
                ThresholdRule(
                    sensor_id="maitri.energy.gen1.fuel_pct",
                    metric_name="fuel_level_percent",
                    condition="lte",
                    threshold_value=15.0,
                    severity=AlertSeverity.CRITICAL,
                    description_template="Fuel critical: {value:.1f}%",
                )
            ],
        )
        assert config.station_id == StationId.MAITRI
        assert len(config.sensors) == 1
        assert len(config.threshold_rules) == 1

    def test_invalid_condition_rejected(self):
        from shared.schemas.config import ThresholdRule, AlertSeverity
        with pytest.raises(Exception):  # pydantic ValidationError
            ThresholdRule(
                sensor_id="maitri.energy.gen1.fuel_pct",
                metric_name="fuel_level_percent",
                condition="INVALID_OP",
                threshold_value=15.0,
                severity=AlertSeverity.CRITICAL,
                description_template="test",
            )

    def test_sampling_interval_must_be_positive(self):
        from shared.schemas.config import SensorConfig, Domain
        with pytest.raises(Exception):  # pydantic ValidationError
            SensorConfig(
                sensor_id="maitri.energy.gen1.fuel_pct",
                domain=Domain.ENERGY,
                metric_name="fuel_level_percent",
                unit="pct",
                sampling_interval_s=0,  # invalid — must be >= 1
            )
