"""Phase 2 unit tests — Edge backend core (no infrastructure required).

Tests cover:
 - Threshold evaluator: all six conditions, multi-rule, no false positives
 - Rate-of-change evaluator: max/min rate breach and clear
 - IngestionService._reading_to_row(): field mapping correctness
 - AlertCandidate dataclass construction
 - EdgeConfig validation (STATION_ID guard)
 - Redis channel name helpers
 - Black-box hash chain integration with BlackBoxLogger frame computation
 - Edge API schema computed fields (AlertOut.duration_open_s)

Run with: pytest tests/unit/test_phase2_edge.py -v
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from edge.alert_engine.evaluator import (
    AlertCandidate,
    evaluate_rate_of_change,
    evaluate_thresholds,
)
from edge.redis_client import alerts_channel, dedup_key, queue_key, sensor_channel
from shared.utils.time import utcnow


# ---------------------------------------------------------------------------
# Helpers — build minimal ThresholdRule and RateOfChangeRule without YAML
# ---------------------------------------------------------------------------

def _make_threshold_rule(
    sensor_id: str,
    condition: str,
    threshold_value: float,
    severity: str = "HIGH",
    description_template: str = "Sensor {value:.1f} {condition} {threshold}",
) -> object:
    """Create a ThresholdRule-compatible object from shared.schemas.config."""
    from shared.schemas.config import AlertSeverity, ThresholdRule
    return ThresholdRule(
        sensor_id=sensor_id,
        metric_name="test_metric",
        condition=condition,
        threshold_value=threshold_value,
        severity=AlertSeverity(severity),
        description_template=description_template,
    )


def _make_roc_rule(
    max_rate_per_minute: float,
    severity: str = "MEDIUM",
    sensor_id: str = "maitri.energy.gen1.fuel_pct",
) -> object:
    """Create a RateOfChangeRule matching the actual schema in shared.schemas.config."""
    from shared.schemas.config import AlertSeverity, RateOfChangeRule
    return RateOfChangeRule(
        sensor_id=sensor_id,
        max_rate_per_minute=max_rate_per_minute,
        severity=AlertSeverity(severity),
        description_template="Rate {value:.2f}/min exceeds {threshold}/min",
    )


def _make_reading(
    sensor_id: str = "maitri.energy.gen1.fuel_pct",
    value: float = 50.0,
    domain: str = "energy",
    asset_id: str | None = "maitri.gen1",
) -> dict:
    return {
        "station_id": "maitri",
        "sensor_id": sensor_id,
        "domain": domain,
        "metric_name": "fuel_level_percent",
        "value": value,
        "unit": "pct",
        "quality": "NOMINAL",
        "asset_id": asset_id,
        "timestamp_utc": utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Threshold evaluator — condition correctness
# ---------------------------------------------------------------------------

class TestThresholdEvaluator:
    def test_lte_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 15.0, "CRITICAL")
        reading = _make_reading(value=10.0)
        candidates = evaluate_thresholds(reading, [rule])
        assert len(candidates) == 1
        assert candidates[0].severity.value == "CRITICAL"

    def test_lte_not_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 15.0)
        reading = _make_reading(value=20.0)
        assert evaluate_thresholds(reading, [rule]) == []

    def test_gte_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "gte", 90.0)
        reading = _make_reading(value=95.0)
        assert len(evaluate_thresholds(reading, [rule])) == 1

    def test_gte_not_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "gte", 90.0)
        reading = _make_reading(value=85.0)
        assert evaluate_thresholds(reading, [rule]) == []

    def test_gt_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "gt", 85.0)
        reading = _make_reading(value=86.0)
        assert len(evaluate_thresholds(reading, [rule])) == 1

    def test_lt_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lt", 30.0, "HIGH")
        reading = _make_reading(value=25.0)
        candidates = evaluate_thresholds(reading, [rule])
        assert len(candidates) == 1
        assert candidates[0].severity.value == "HIGH"

    def test_eq_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.gen_status", "eq", 2.0, "CRITICAL")
        reading = _make_reading(sensor_id="maitri.energy.gen1.gen_status", value=2.0)
        assert len(evaluate_thresholds(reading, [rule])) == 1

    def test_eq_not_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.gen_status", "eq", 2.0, "CRITICAL")
        reading = _make_reading(sensor_id="maitri.energy.gen1.gen_status", value=1.0)
        assert evaluate_thresholds(reading, [rule]) == []

    def test_neq_breached(self):
        rule = _make_threshold_rule("maitri.energy.gen1.gen_status", "neq", 1.0)
        reading = _make_reading(sensor_id="maitri.energy.gen1.gen_status", value=0.0)
        assert len(evaluate_thresholds(reading, [rule])) == 1

    def test_wrong_sensor_id_skipped(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 15.0)
        reading = _make_reading(sensor_id="maitri.energy.gen2.fuel_pct", value=5.0)
        assert evaluate_thresholds(reading, [rule]) == []

    def test_multiple_rules_multiple_breaches(self):
        """Both LOW and HIGH rules fire for the same reading."""
        rules = [
            _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 30.0, "HIGH"),
            _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 15.0, "CRITICAL"),
        ]
        reading = _make_reading(value=10.0)
        candidates = evaluate_thresholds(reading, rules)
        assert len(candidates) == 2
        severities = {c.severity.value for c in candidates}
        assert "HIGH" in severities
        assert "CRITICAL" in severities

    def test_description_template_formatted(self):
        rule = _make_threshold_rule(
            "maitri.energy.gen1.fuel_pct", "lte", 15.0,
            description_template="Fuel at {value:.1f}%"
        )
        reading = _make_reading(value=10.5)
        candidates = evaluate_thresholds(reading, [rule])
        assert "10.5%" in candidates[0].description

    def test_no_rules_returns_empty(self):
        reading = _make_reading(value=10.0)
        assert evaluate_thresholds(reading, []) == []

    def test_candidate_contains_rule_id(self):
        rule = _make_threshold_rule("maitri.energy.gen1.fuel_pct", "lte", 15.0)
        reading = _make_reading(value=10.0)
        candidate = evaluate_thresholds(reading, [rule])[0]
        assert "maitri.energy.gen1.fuel_pct" in candidate.rule_id
        assert "lte" in candidate.rule_id
        assert "15.0" in candidate.rule_id


# ---------------------------------------------------------------------------
# Rate-of-change evaluator
# ---------------------------------------------------------------------------

class TestRateOfChangeEvaluator:
    def test_rate_exceeded_breached(self):
        """Rate of change (abs value) exceeds the threshold → alert raised."""
        rule = _make_roc_rule(max_rate_per_minute=2.0)
        reading = _make_reading(value=20.0)
        # prev=10, dt=60s → rate = (20-10)/60 * 60 = 10/min > 2/min
        candidates = evaluate_rate_of_change(reading, prev_value=10.0, delta_s=60.0, rules=[rule])
        assert len(candidates) == 1
        assert candidates[0].condition == "roc_exceeded"

    def test_rate_not_breached(self):
        rule = _make_roc_rule(max_rate_per_minute=20.0)
        reading = _make_reading(value=11.0)
        # rate = (11-10)/60 * 60 = 1/min < 20/min → no breach
        candidates = evaluate_rate_of_change(reading, prev_value=10.0, delta_s=60.0, rules=[rule])
        assert candidates == []

    def test_negative_rate_also_detected(self):
        """A rapid drop (negative rate) should also trigger via abs() comparison."""
        rule = _make_roc_rule(max_rate_per_minute=2.0)
        reading = _make_reading(value=0.0)
        # prev=20, dt=60s → rate = (0-20)/60 * 60 = -20/min, abs=20 > 2
        candidates = evaluate_rate_of_change(reading, prev_value=20.0, delta_s=60.0, rules=[rule])
        assert len(candidates) == 1

    def test_zero_delta_s_returns_empty(self):
        rule = _make_roc_rule(max_rate_per_minute=2.0)
        reading = _make_reading(value=20.0)
        assert evaluate_rate_of_change(reading, prev_value=10.0, delta_s=0.0, rules=[rule]) == []

    def test_no_rules_returns_empty(self):
        reading = _make_reading(value=20.0)
        assert evaluate_rate_of_change(reading, prev_value=10.0, delta_s=60.0, rules=[]) == []


# ---------------------------------------------------------------------------
# IngestionService._reading_to_row()
# ---------------------------------------------------------------------------

class TestReadingToRow:
    def test_iso_timestamp_parsed(self):
        from edge.ingestion.service import _reading_to_row
        reading = _make_reading(value=85.0)
        reading["timestamp_utc"] = "2026-08-27T09:00:00Z"
        row = _reading_to_row(reading)
        assert isinstance(row["timestamp_utc"], datetime)
        assert row["timestamp_utc"].tzinfo is not None

    def test_all_required_fields_present(self):
        from edge.ingestion.service import _reading_to_row
        reading = _make_reading(value=85.0)
        row = _reading_to_row(reading)
        for field in ("station_id", "sensor_id", "domain", "metric_name",
                      "value", "unit", "quality", "timestamp_utc", "is_aggregate"):
            assert field in row, f"Missing field: {field}"

    def test_value_is_float(self):
        from edge.ingestion.service import _reading_to_row
        reading = _make_reading(value=42)   # int → should be cast to float
        row = _reading_to_row(reading)
        assert isinstance(row["value"], float)

    def test_empty_asset_id_becomes_none(self):
        from edge.ingestion.service import _reading_to_row
        reading = _make_reading(value=85.0)
        reading["asset_id"] = ""
        row = _reading_to_row(reading)
        assert row["asset_id"] is None


# ---------------------------------------------------------------------------
# Redis channel name helpers
# ---------------------------------------------------------------------------

class TestRedisHelpers:
    def test_sensor_channel_format(self):
        assert sensor_channel("maitri", "energy") == "sensor:maitri:energy"

    def test_alerts_channel_format(self):
        assert alerts_channel("bharati") == "alerts:bharati"

    def test_queue_key_format(self):
        assert queue_key("maitri") == "queue:outbound:maitri"

    def test_dedup_key_format(self):
        key = dedup_key("maitri", "my.sensor:lte:15.0", "my.sensor")
        assert key.startswith("dedup:alert:maitri:")
        assert "my.sensor" in key

    def test_channels_are_station_scoped(self):
        """Maitri and Bharati channels must never be equal."""
        assert sensor_channel("maitri", "energy") != sensor_channel("bharati", "energy")
        assert alerts_channel("maitri") != alerts_channel("bharati")


# ---------------------------------------------------------------------------
# EdgeConfig validation
# ---------------------------------------------------------------------------

class TestEdgeConfig:
    def test_invalid_station_id_raises(self):
        import os
        with patch.dict(os.environ, {"STATION_ID": "invalid_station"}):
            from edge.config import EdgeConfig
            with pytest.raises(RuntimeError, match="STATION_ID"):
                EdgeConfig()

    def test_maitri_display_name(self):
        import os
        with patch.dict(os.environ, {
            "STATION_ID": "maitri",
            "DATABASE_URL": "postgresql://u:p@localhost/db",
            "REDIS_URL": "redis://localhost:6380/0",
        }):
            from edge.config import EdgeConfig
            cfg = EdgeConfig()
            assert "Maitri" in cfg.display_name

    def test_bharati_display_name(self):
        import os
        with patch.dict(os.environ, {
            "STATION_ID": "bharati",
            "DATABASE_URL": "postgresql://u:p@localhost/db",
            "REDIS_URL": "redis://localhost:6380/0",
        }):
            from edge.config import EdgeConfig
            cfg = EdgeConfig()
            assert "Bharati" in cfg.display_name


# ---------------------------------------------------------------------------
# AlertOut schema computed field
# ---------------------------------------------------------------------------

class TestAlertOutSchema:
    def _make_alert_dict(self, **overrides) -> dict:
        base = {
            "alert_id": "maitri-energy-1234567890-abcd",
            "station_id": "maitri",
            "severity": "HIGH",
            "domain": "energy",
            "asset_id": "maitri.gen1",
            "triggered_at": utcnow() - timedelta(minutes=5),
            "description": "Test alert",
            "ack_state": "OPEN",
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "black_box_activated": False,
            "synced_to_cloud": False,
        }
        base.update(overrides)
        return base

    def test_duration_open_s_for_unresolved(self):
        from edge.api.schemas import AlertOut
        data = self._make_alert_dict()
        alert = AlertOut(**data)
        # Alert has been open ~5 minutes (300 seconds)
        assert 290 <= alert.duration_open_s <= 310

    def test_duration_open_s_for_resolved(self):
        from edge.api.schemas import AlertOut
        triggered = utcnow() - timedelta(minutes=10)
        resolved = triggered + timedelta(minutes=3)
        data = self._make_alert_dict(triggered_at=triggered, resolved_at=resolved)
        alert = AlertOut(**data)
        # Resolved after 3 minutes = 180 seconds
        assert abs(alert.duration_open_s - 180) < 2

    def test_alert_out_fields_present(self):
        from edge.api.schemas import AlertOut
        data = self._make_alert_dict()
        alert = AlertOut(**data)
        assert alert.alert_id == data["alert_id"]
        assert alert.severity == "HIGH"
        assert alert.ack_state == "OPEN"


# ---------------------------------------------------------------------------
# Black-box hash chain: frame computation (unit-level)
# ---------------------------------------------------------------------------

class TestBlackBoxFrameComputation:
    def test_initial_prev_hash_is_deterministic(self):
        from shared.crypto.hash_chain import initial_prev_hash
        h1 = initial_prev_hash("maitri-energy-123-abcd")
        h2 = initial_prev_hash("maitri-energy-123-abcd")
        assert h1 == h2

    def test_frame_hash_changes_with_content(self):
        from shared.crypto.hash_chain import compute_frame_hash
        h1 = compute_frame_hash(b"frame content A")
        h2 = compute_frame_hash(b"frame content B")
        assert h1 != h2

    def test_simulated_3_frame_chain(self):
        from shared.crypto.hash_chain import (
            compute_frame_hash, initial_prev_hash, verify_chain
        )
        trigger = "maitri-energy-1724745600000-a3f1"
        frames = []
        prev = initial_prev_hash(trigger)
        for i in range(3):
            content = f"frame-{i}-data".encode()
            fh = compute_frame_hash(content)
            frames.append({
                "frame_index": i,
                "trigger_alert_id": trigger,
                "prev_hash": prev,
                "frame_hash": fh,
                "frame_bytes_without_hash": content,
            })
            prev = fh
        valid, reason = verify_chain(frames)
        assert valid, f"Chain should be valid but got: {reason}"
