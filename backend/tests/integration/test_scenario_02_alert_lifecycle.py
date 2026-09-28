"""Integration Scenario 02 — Alert Lifecycle.

Uses the real evaluate_thresholds() / evaluate_rate_of_change() functions.
"""
from __future__ import annotations

from typing import List

import pytest

from shared.schemas.config import RateOfChangeRule, ThresholdRule
from edge.alert_engine.evaluator import (
    AlertCandidate,
    evaluate_thresholds,
    evaluate_rate_of_change,
)


def _rule(
    condition="lt",
    threshold=30.0,
    severity="HIGH",
    sensor_id="maitri.energy.gen1.fuel_pct",
    domain="energy",
    rule_id="r1",
    metric_name="fuel_level_percent",
    asset_id="maitri.gen1",
):
    return ThresholdRule(
        rule_id=rule_id,
        sensor_id=sensor_id,
        metric_name=metric_name,
        condition=condition,
        threshold_value=threshold,
        severity=severity,
        domain=domain,
        asset_id=asset_id,
        description_template="Sensor {value:.1f} vs threshold {threshold:.1f}",
    )


def _roc_rule(max_rate=5.0, severity="HIGH", sensor_id="maitri.energy.gen1.fuel_pct"):
    return RateOfChangeRule(
        rule_id="roc1",
        sensor_id=sensor_id,
        max_rate_per_minute=max_rate,
        severity=severity,
        description_template="Rate {value:.2f}/min exceeds {threshold:.2f}/min",
    )


def _reading(value=25.0, sensor_id="maitri.energy.gen1.fuel_pct", domain="energy"):
    return {
        "sensor_id": sensor_id,
        "value": value,
        "domain": domain,
        "asset_id": "maitri.gen1",
    }


class TestThresholdEvaluatorScenarios:
    """Scenario 02A — evaluate_thresholds() fires for breached rules."""

    def test_lt_breach_returns_candidate(self):
        candidates = evaluate_thresholds(_reading(value=25.0), [_rule(condition="lt", threshold=30.0)])
        assert len(candidates) == 1

    def test_critical_breach_at_low_fuel(self):
        candidates = evaluate_thresholds(_reading(value=14.0), [_rule(condition="lt", threshold=15.0, severity="CRITICAL")])
        assert len(candidates) == 1

    def test_no_breach_above_threshold(self):
        candidates = evaluate_thresholds(_reading(value=50.0), [_rule(condition="lt", threshold=30.0)])
        assert len(candidates) == 0

    def test_gt_breach(self):
        candidates = evaluate_thresholds(
            _reading(value=35.0, sensor_id="maitri.env.temp_c", domain="environment"),
            [_rule(condition="gt", threshold=30.0, sensor_id="maitri.env.temp_c", domain="environment", metric_name="room_temp")],
        )
        assert len(candidates) == 1

    def test_eq_breach(self):
        candidates = evaluate_thresholds(_reading(value=1.0), [_rule(condition="eq", threshold=1.0, severity="CRITICAL")])
        assert len(candidates) == 1

    def test_neq_breach(self):
        candidates = evaluate_thresholds(_reading(value=1.0), [_rule(condition="neq", threshold=0.0, severity="MEDIUM")])
        assert len(candidates) == 1

    def test_gte_at_boundary(self):
        candidates = evaluate_thresholds(_reading(value=30.0), [_rule(condition="gte", threshold=30.0, severity="MEDIUM")])
        assert len(candidates) == 1

    def test_lte_at_boundary(self):
        candidates = evaluate_thresholds(_reading(value=30.0), [_rule(condition="lte", threshold=30.0, severity="MEDIUM")])
        assert len(candidates) == 1

    def test_wrong_sensor_id_skipped(self):
        candidates = evaluate_thresholds(
            _reading(value=5.0),
            [_rule(sensor_id="other.sensor.somewhere")],
        )
        assert len(candidates) == 0

    def test_multiple_rules_multiple_breaches(self):
        candidates = evaluate_thresholds(
            _reading(value=10.0),
            [
                _rule(rule_id="r1", condition="lt", threshold=30.0, severity="HIGH"),
                _rule(rule_id="r2", condition="lt", threshold=15.0, severity="CRITICAL"),
            ],
        )
        assert len(candidates) == 2

    def test_alert_candidate_has_required_fields(self):
        candidates = evaluate_thresholds(_reading(value=10.0), [_rule(condition="lt", threshold=30.0)])
        c = candidates[0]
        for attr in ("rule_id", "sensor_id", "domain", "severity", "description"):
            assert hasattr(c, attr), f"AlertCandidate missing field: {attr}"

    def test_description_is_non_empty(self):
        candidates = evaluate_thresholds(_reading(value=10.0), [_rule(condition="lt", threshold=30.0)])
        assert candidates[0].description.strip() != ""

    def test_reading_value_captured(self):
        candidates = evaluate_thresholds(_reading(value=22.5), [_rule(condition="lt", threshold=30.0)])
        assert candidates[0].reading_value == 22.5

    def test_threshold_value_captured(self):
        candidates = evaluate_thresholds(_reading(value=10.0), [_rule(condition="lt", threshold=30.0)])
        assert candidates[0].threshold_value == 30.0

    def test_no_alert_when_rules_list_empty(self):
        candidates = evaluate_thresholds(_reading(value=5.0), [])
        assert candidates == []


class TestRateOfChangeEvaluator:
    """Scenario 02B — evaluate_rate_of_change() via real function (sync)."""

    def test_fast_fuel_drain_triggers(self):
        """60% → 50% in 60s = 10%/min, threshold 5%/min → HIGH alert."""
        rule = _roc_rule(max_rate=5.0, severity="HIGH")
        candidates = evaluate_rate_of_change(
            reading=_reading(value=50.0),
            prev_value=60.0,
            delta_s=60.0,
            rules=[rule],
        )
        assert len(candidates) == 1

    def test_slow_drain_no_alert(self):
        """59% → 60% in 60s = 1%/min, threshold 5%/min → no alert."""
        rule = _roc_rule(max_rate=5.0)
        candidates = evaluate_rate_of_change(
            reading=_reading(value=59.0),
            prev_value=60.0,
            delta_s=60.0,
            rules=[rule],
        )
        assert len(candidates) == 0

    def test_zero_delta_returns_empty(self):
        """delta_s=0 protected against ZeroDivisionError."""
        rule = _roc_rule(max_rate=5.0)
        candidates = evaluate_rate_of_change(
            reading=_reading(value=50.0),
            prev_value=60.0,
            delta_s=0,
            rules=[rule],
        )
        assert candidates == []

    def test_rapid_increase_also_triggers(self):
        """Absolute rate check — rapid increase also fires."""
        rule = _roc_rule(max_rate=5.0)
        candidates = evaluate_rate_of_change(
            reading=_reading(value=70.0),
            prev_value=60.0,
            delta_s=60.0,
            rules=[rule],
        )
        assert len(candidates) == 1

    def test_roc_candidate_condition_label(self):
        rule = _roc_rule(max_rate=5.0)
        candidates = evaluate_rate_of_change(
            reading=_reading(value=50.0),
            prev_value=60.0,
            delta_s=60.0,
            rules=[rule],
        )
        assert candidates[0].condition == "roc_exceeded"

    def test_no_roc_rules_returns_empty(self):
        candidates = evaluate_rate_of_change(
            reading=_reading(value=50.0),
            prev_value=60.0,
            delta_s=60.0,
            rules=[],
        )
        assert candidates == []


class TestAlertIdGeneration:
    """Scenario 02C — Alert ID uniqueness and format."""

    def test_alert_id_ends_with_8_hex_chars(self):
        from shared.utils.alert_id import generate_alert_id
        aid = generate_alert_id("maitri", "energy")
        hex_part = aid.split("-")[-1]
        assert len(hex_part) == 8
        int(hex_part, 16)  # valid hex

    def test_alert_ids_are_unique_across_100_calls(self):
        from shared.utils.alert_id import generate_alert_id
        ids = {generate_alert_id("maitri", "energy") for _ in range(100)}
        assert len(ids) == 100

    def test_alert_id_contains_station_id(self):
        from shared.utils.alert_id import generate_alert_id
        aid = generate_alert_id("maitri", "energy")
        assert "maitri" in aid

    def test_alert_id_contains_domain(self):
        from shared.utils.alert_id import generate_alert_id
        aid = generate_alert_id("maitri", "weather")
        assert "weather" in aid

    def test_bharati_alert_id_distinct_from_maitri(self):
        from shared.utils.alert_id import generate_alert_id
        m = generate_alert_id("maitri", "energy")
        b = generate_alert_id("bharati", "energy")
        assert "maitri" in m
        assert "bharati" in b
