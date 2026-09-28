"""Threshold rule evaluator for the Edge alert engine.

Stateless: given a sensor reading dict and a list of ThresholdRule objects,
returns a list of AlertCandidate objects for each rule that is currently
breached by the reading.

Supported conditions (from StationConfig ThresholdRule):
  gt  — value > threshold
  gte — value >= threshold
  lt  — value < threshold
  lte — value <= threshold
  eq  — value == threshold (useful for state sensors like fire, generator status)
  ne  — value != threshold

Rate-of-change rules (RateOfChangeRule) are evaluated by the caller
who must supply the previous value and the time delta.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from shared.schemas.config import AlertSeverity, RateOfChangeRule, ThresholdRule


@dataclass
class AlertCandidate:
    """A potential alert from a threshold breach."""
    rule_id: str           # unique identifier for this rule (used for dedup)
    sensor_id: str
    domain: str
    asset_id: Optional[str]
    severity: AlertSeverity
    description: str       # formatted description_template
    reading_value: float
    threshold_value: float
    condition: str


_OPS = {
    "gt":  lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "lt":  lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "eq":  lambda v, t: abs(v - t) < 1e-9,
    "neq": lambda v, t: abs(v - t) >= 1e-9,
}


def evaluate_thresholds(
    reading: dict,
    rules: List[ThresholdRule],
) -> List[AlertCandidate]:
    """Return AlertCandidates for each threshold rule breached by the reading.

    Only rules whose sensor_id matches the reading's sensor_id are evaluated.
    """
    sensor_id = reading.get("sensor_id", "")
    value = reading.get("value", 0.0)
    domain = reading.get("domain", "")
    asset_id = reading.get("asset_id") or None
    candidates: List[AlertCandidate] = []

    for rule in rules:
        if rule.sensor_id != sensor_id:
            continue
        op = _OPS.get(rule.condition)
        if op is None:
            continue
        if op(value, rule.threshold_value):
            description = _format_description(rule.description_template, value, rule)
            rule_id = f"{sensor_id}:{rule.condition}:{rule.threshold_value}"
            candidates.append(AlertCandidate(
                rule_id=rule_id,
                sensor_id=sensor_id,
                domain=domain,
                asset_id=asset_id,
                severity=rule.severity,
                description=description,
                reading_value=value,
                threshold_value=rule.threshold_value,
                condition=rule.condition,
            ))

    return candidates


def evaluate_rate_of_change(
    reading: dict,
    prev_value: float,
    delta_s: float,
    rules: List[RateOfChangeRule],
) -> List[AlertCandidate]:
    """Evaluate rate-of-change rules.

    RateOfChangeRule has no sensor_id — it applies to whatever sensor is passed.
    Typically the caller filters rules to those relevant for the reading's metric.

    Args:
        reading: Current SensorReading dict.
        prev_value: Previous value of the same sensor.
        delta_s: Seconds elapsed since prev_value was read.
        rules: Rate-of-change rules from station config.
    """
    if delta_s <= 0:
        return []

    sensor_id = reading.get("sensor_id", "")
    value = reading.get("value", 0.0)
    domain = reading.get("domain", "")
    asset_id = reading.get("asset_id") or None
    # rate rules use per-minute rates in config
    rate_per_min = (value - prev_value) / delta_s * 60.0
    candidates: List[AlertCandidate] = []

    for rule in rules:
        # RateOfChangeRule: only has max_rate_per_minute (always positive threshold)
        threshold = rule.max_rate_per_minute
        # Breach if absolute rate of change exceeds threshold
        if abs(rate_per_min) > threshold:
            rule_id = f"{sensor_id}:roc:{threshold}"
            description = rule.description_template.format(
                value=rate_per_min, threshold=threshold, sensor_id=sensor_id
            )
            candidates.append(AlertCandidate(
                rule_id=rule_id,
                sensor_id=sensor_id,
                domain=domain,
                asset_id=asset_id,
                severity=rule.severity,
                description=description,
                reading_value=rate_per_min,
                threshold_value=threshold,
                condition="roc_exceeded",
            ))

    return candidates


def _format_description(template: str, value: float, rule: ThresholdRule) -> str:
    """Format the description template with current sensor value."""
    try:
        return template.format(
            value=value,
            threshold=rule.threshold_value,
            condition=rule.condition,
        )
    except (KeyError, ValueError):
        return template
