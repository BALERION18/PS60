"""Feature builder for the Edge AI Engine.

Converts raw sensor reading dicts (as published on Redis) into
normalised numpy feature vectors for ML model inference.

Feature vector layout (fixed order — NEVER change order after training,
retrain the model if you need to add/remove features):

    Index  Sensor field             Range (normalised to 0-1)
    -----  ----------------------   -------------------------
    0      vibration_rms (mm/s)     0 – 30
    1      oil_pressure_bar         0 – 10
    2      coolant_temp_c           0 – 120  (shifted: sensor reads 70-110)
    3      power_output_kw          0 – 250
    4      fuel_consumption_lph     0 – 60

Each feature is clipped to its valid range then divided by max_range so
values always land in [0, 1].  Missing sensors get their nominal midpoint
(0.5) so a partial reading doesn't break inference.

The StateBuffer class accumulates multiple readings per asset so the
feature vector for a *window* of readings can be built (mean + std of
each feature over the last N readings).  This is important for the
Isolation Forest because a single spike is often noise — a sustained
deviation over 10 readings is a real anomaly.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Feature spec (name, sensor_id suffix, clip_max, nominal_value)
# ---------------------------------------------------------------------------
# nominal_value is used when a reading for that sensor is missing.
# clip_max is the physical maximum we ever expect to see.

FEATURE_SPEC: List[Tuple[str, str, float, float]] = [
    # (feature_name, sensor_id_suffix, clip_max, nominal_value)
    ("vibration_rms",        "vibration_rms",        30.0,   2.0),
    ("oil_pressure_bar",     "oil_pressure_bar",     10.0,   4.5),
    ("coolant_temp_c",       "coolant_temp_c",      120.0,  85.0),
    ("power_output_kw",      "power_output_kw",     250.0, 100.0),
    ("fuel_consumption_lph", "fuel_consumption_lph", 60.0,  15.0),
]

FEATURE_NAMES: List[str] = [f[0] for f in FEATURE_SPEC]
N_FEATURES: int = len(FEATURE_SPEC)

# Window size for StateBuffer: keep last N readings per asset
WINDOW_SIZE: int = 10


def _clip_normalise(value: float, clip_max: float) -> float:
    """Clip value to [0, clip_max] and normalise to [0, 1]."""
    clipped = max(0.0, min(value, clip_max))
    return clipped / clip_max if clip_max > 0 else 0.0


def reading_to_feature_vector(
    readings_by_suffix: Dict[str, float],
) -> np.ndarray:
    """Build a single feature vector from a dict of {sensor_suffix: value}.

    Args:
        readings_by_suffix: e.g. {"vibration_rms": 8.5, "oil_pressure_bar": 4.1, ...}
            Any missing key gets the nominal midpoint for that feature.

    Returns:
        numpy array of shape (N_FEATURES,) with values in [0, 1].
    """
    vec = np.empty(N_FEATURES, dtype=np.float32)
    for i, (_, suffix, clip_max, nominal) in enumerate(FEATURE_SPEC):
        raw = readings_by_suffix.get(suffix, nominal)
        vec[i] = _clip_normalise(float(raw), clip_max)
    return vec


def window_to_feature_vector(
    window: List[np.ndarray],
) -> np.ndarray:
    """Summarise a window of feature vectors into a single row.

    Concatenates per-feature [mean, std] → shape (2 * N_FEATURES,).
    Std is 0 when window has only one reading.
    """
    matrix = np.stack(window, axis=0)          # (W, N_FEATURES)
    mean = matrix.mean(axis=0)                  # (N_FEATURES,)
    std  = matrix.std(axis=0)                   # (N_FEATURES,)
    return np.concatenate([mean, std])           # (2 * N_FEATURES,)


# ---------------------------------------------------------------------------
# StateBuffer — per-asset rolling window of readings
# ---------------------------------------------------------------------------

class StateBuffer:
    """Accumulates readings for one asset and builds windowed feature vectors.

    Usage:
        buf = StateBuffer(asset_id="maitri.gen1")
        buf.update("vibration_rms", 8.5)
        buf.update("oil_pressure_bar", 4.2)
        ...
        vec = buf.get_window_vector()   # None until window is full
    """

    def __init__(self, asset_id: str, window: int = WINDOW_SIZE) -> None:
        self.asset_id = asset_id
        self._window = window
        # ring buffer of per-reading feature vectors
        self._ring: Deque[np.ndarray] = deque(maxlen=window)
        # accumulator for current reading (reset on flush)
        self._current: Dict[str, float] = {}

    def update(self, sensor_suffix: str, value: float) -> None:
        """Update the current reading with a sensor value."""
        self._current[sensor_suffix] = value

    def flush(self) -> None:
        """Finalise the current reading and push to ring buffer."""
        vec = reading_to_feature_vector(self._current)
        self._ring.append(vec)
        self._current = {}

    def update_and_flush(self, readings_by_suffix: Dict[str, float]) -> None:
        """Convenience: update all sensors at once and flush."""
        self._current.update(readings_by_suffix)
        self.flush()

    @property
    def is_ready(self) -> bool:
        """True once the ring buffer holds at least one reading."""
        return len(self._ring) > 0

    @property
    def is_window_full(self) -> bool:
        return len(self._ring) == self._window

    def get_latest_vector(self) -> Optional[np.ndarray]:
        """Return the most recent single reading vector (N_FEATURES,)."""
        if not self._ring:
            return None
        return self._ring[-1]

    def get_window_vector(self) -> Optional[np.ndarray]:
        """Return windowed summary vector (2*N_FEATURES,) or None if empty."""
        if not self._ring:
            return None
        return window_to_feature_vector(list(self._ring))


# ---------------------------------------------------------------------------
# Sensor-id helpers
# ---------------------------------------------------------------------------

def extract_suffix(sensor_id: str) -> str:
    """Extract the last component of a dotted sensor_id.

    e.g. "maitri.energy.gen1.oil_pressure_bar" → "oil_pressure_bar"
    """
    return sensor_id.rsplit(".", 1)[-1]


def is_generator_sensor(sensor_id: str) -> bool:
    """Return True if this sensor belongs to a generator asset."""
    return ".gen" in sensor_id


def asset_id_from_sensor(sensor_id: str) -> str:
    """Extract the asset portion of a sensor_id.

    e.g. "maitri.energy.gen1.oil_pressure_bar" → "maitri.gen1"
         "bharati.energy.gen2.fuel_pct"         → "bharati.gen2"
    """
    parts = sensor_id.split(".")
    # format: {station}.{domain}.{asset}.{metric}
    if len(parts) >= 3:
        return f"{parts[0]}.{parts[2]}"
    return sensor_id
