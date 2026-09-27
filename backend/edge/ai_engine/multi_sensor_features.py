"""Multi-sensor feature builder for LSTM Autoencoder (Model 3).

Covers all continuous sensor channels across energy, weather, and
environment domains for both stations.

Feature vector layout — Maitri (15 channels):
    Index  Sensor                          Nominal range     Clip max
    -----  ------------------------------  ---------------   --------
    0      gen1.fuel_pct                   0–100 %           100
    1      gen1.power_output_kw            0–150 kW          200
    2      gen1.fuel_consumption_lph       0–30 L/h          60
    3      gen1.oil_pressure_bar           3–6 bar           10
    4      gen1.coolant_temp_c             70–100 °C         120
    5      gen2.power_output_kw            0–150 kW          200
    6      grid.total_load_kw              0–200 kW          300
    7      ambient_temp_c                  -60–10 °C         [shift: +70 / 80]
    8      wind_speed_ms                   0–80 m/s          80
    9      pressure_hpa                    950–1040 hPa      [shift: -950 / 90]
    10     humidity_pct                    0–100 %           100
    11     co2_ppm                         350–1500 ppm      [shift: -350 / 1150]
    12     co_ppm                          0–35 ppm          100
    13     pm25_ugm3                       0–35 µg/m³        100
    14     seismic_magnitude               0–10 Richter      10

Feature vector layout — Bharati (13 channels):
    Index  Sensor                          Nominal range     Clip max
    -----  ------------------------------  ---------------   --------
    0      gen1.fuel_pct                   0–100 %           100
    1      gen1.power_output_kw            0–250 kW          300
    2      gen1.fuel_consumption_lph       0–50 L/h          80
    3      solar1.output_kw                0–50 kW           60
    4      solar1.irradiance_wm2           0–1200 W/m²       1400
    5      grid.total_load_kw              0–300 kW          400
    6      ambient_temp_c                  -40–10 °C         (shifted)
    7      wind_speed_ms                   0–70 m/s          80
    8      pressure_hpa                    960–1040 hPa      (shifted)
    9      humidity_pct                    0–100 %           100
    10     uv_index                        0–12 UVI          15
    11     co2_ppm                         350–1500 ppm      (shifted)
    12     co_ppm                          0–35 ppm          100

All values normalised to [0, 1]. Shifted channels: (value - shift_min) / range.
Sequence length: 30 time-steps (5 minutes of 10s energy readings).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Feature specs per station
# Each entry: (feature_name, sensor_suffix, shift_min, value_range)
# normalised = clip((value - shift_min) / value_range, 0, 1)
# ---------------------------------------------------------------------------

MAITRI_FEATURE_SPEC: List[Tuple[str, str, float, float]] = [
    ("gen1_fuel_pct",          "gen1.fuel_pct",            0.0,   100.0),
    ("gen1_power_kw",          "gen1.power_output_kw",     0.0,   200.0),
    ("gen1_fuel_lph",          "gen1.fuel_consumption_lph",0.0,   60.0),
    ("gen1_oil_bar",           "gen1.oil_pressure_bar",    0.0,   10.0),
    ("gen1_coolant_c",         "gen1.coolant_temp_c",      0.0,   120.0),
    ("gen2_power_kw",          "gen2.power_output_kw",     0.0,   200.0),
    ("grid_load_kw",           "grid.total_load_kw",       0.0,   300.0),
    ("ambient_temp_c",         "ambient_temp_c",          -70.0,  80.0),
    ("wind_speed_ms",          "wind_speed_ms",            0.0,   80.0),
    ("pressure_hpa",           "pressure_hpa",            940.0,  100.0),
    ("humidity_pct",           "humidity_pct",             0.0,   100.0),
    ("co2_ppm",                "co2_ppm",                350.0, 1150.0),
    ("co_ppm",                 "co_ppm",                   0.0,   100.0),
    ("pm25_ugm3",              "pm25_ugm3",                0.0,   100.0),
    ("seismic_magnitude",      "seismic_magnitude",        0.0,   10.0),
]

BHARATI_FEATURE_SPEC: List[Tuple[str, str, float, float]] = [
    ("gen1_fuel_pct",          "gen1.fuel_pct",            0.0,   100.0),
    ("gen1_power_kw",          "gen1.power_output_kw",     0.0,   300.0),
    ("gen1_fuel_lph",          "gen1.fuel_consumption_lph",0.0,   80.0),
    ("solar_output_kw",        "solar1.output_kw",         0.0,   60.0),
    ("solar_irradiance_wm2",   "solar1.irradiance_wm2",    0.0, 1400.0),
    ("grid_load_kw",           "grid.total_load_kw",       0.0,   400.0),
    ("ambient_temp_c",         "ambient_temp_c",          -50.0,  60.0),
    ("wind_speed_ms",          "wind_speed_ms",            0.0,   80.0),
    ("pressure_hpa",           "pressure_hpa",            950.0,  100.0),
    ("humidity_pct",           "humidity_pct",             0.0,   100.0),
    ("uv_index",               "uv_index",                 0.0,   15.0),
    ("co2_ppm",                "co2_ppm",                350.0, 1150.0),
    ("co_ppm",                 "co_ppm",                   0.0,   100.0),
]

STATION_FEATURE_SPECS: Dict[str, List[Tuple[str, str, float, float]]] = {
    "maitri":  MAITRI_FEATURE_SPEC,
    "bharati": BHARATI_FEATURE_SPEC,
}

# Nominal values used when a sensor reading is missing
MAITRI_NOMINALS: Dict[str, float] = {
    "gen1.fuel_pct": 65.0, "gen1.power_output_kw": 100.0,
    "gen1.fuel_consumption_lph": 15.0, "gen1.oil_pressure_bar": 4.5,
    "gen1.coolant_temp_c": 85.0, "gen2.power_output_kw": 80.0,
    "grid.total_load_kw": 140.0, "ambient_temp_c": -15.0,
    "wind_speed_ms": 8.0, "pressure_hpa": 995.0,
    "humidity_pct": 60.0, "co2_ppm": 600.0,
    "co_ppm": 5.0, "pm25_ugm3": 8.0, "seismic_magnitude": 0.0,
}

BHARATI_NOMINALS: Dict[str, float] = {
    "gen1.fuel_pct": 65.0, "gen1.power_output_kw": 150.0,
    "gen1.fuel_consumption_lph": 22.0, "solar1.output_kw": 15.0,
    "solar1.irradiance_wm2": 300.0, "grid.total_load_kw": 180.0,
    "ambient_temp_c": -12.0, "wind_speed_ms": 9.0,
    "pressure_hpa": 1000.0, "humidity_pct": 65.0,
    "uv_index": 2.5, "co2_ppm": 600.0, "co_ppm": 4.0,
}

STATION_NOMINALS = {"maitri": MAITRI_NOMINALS, "bharati": BHARATI_NOMINALS}

# Sequence length: 30 steps × 10s = 5 minutes of data
SEQUENCE_LENGTH = 30


def get_n_features(station_id: str) -> int:
    return len(STATION_FEATURE_SPECS.get(station_id, MAITRI_FEATURE_SPEC))


def normalise_value(value: float, shift_min: float, value_range: float) -> float:
    """Shift and normalise a sensor value to [0, 1]."""
    if value_range <= 0:
        return 0.0
    return float(np.clip((value - shift_min) / value_range, 0.0, 1.0))


def denormalise_value(norm: float, shift_min: float, value_range: float) -> float:
    return float(norm * value_range + shift_min)


def reading_to_multisensor_vector(
    readings: Dict[str, float],
    station_id: str = "maitri",
) -> np.ndarray:
    """Build a normalised multi-sensor feature vector.

    Args:
        readings:   dict of {sensor_suffix: raw_value}
                    e.g. {"gen1.power_output_kw": 105.0, "ambient_temp_c": -22.0, ...}
        station_id: "maitri" or "bharati"

    Returns:
        np.ndarray shape (N_FEATURES,) values in [0, 1]
    """
    spec     = STATION_FEATURE_SPECS.get(station_id, MAITRI_FEATURE_SPEC)
    nominals = STATION_NOMINALS.get(station_id, MAITRI_NOMINALS)
    n        = len(spec)
    vec      = np.empty(n, dtype=np.float32)

    for i, (_, suffix, shift_min, value_range) in enumerate(spec):
        raw = readings.get(suffix, nominals.get(suffix, shift_min + value_range * 0.5))
        vec[i] = normalise_value(float(raw), shift_min, value_range)

    return vec


def sequence_to_array(sequence: List[np.ndarray]) -> np.ndarray:
    """Stack a list of feature vectors into a (T, N_FEATURES) array."""
    return np.stack(sequence, axis=0).astype(np.float32)


# ---------------------------------------------------------------------------
# SequenceBuffer — accumulates readings to build LSTM input sequences
# ---------------------------------------------------------------------------

class SequenceBuffer:
    """Rolling buffer that accumulates multi-sensor readings for LSTM inference.

    Usage:
        buf = SequenceBuffer("maitri")
        buf.update({"gen1.power_output_kw": 105.0, "ambient_temp_c": -22.0, ...})
        if buf.is_ready:
            seq = buf.get_sequence()  # shape (SEQUENCE_LENGTH, N_FEATURES)
            pred = model.predict_sequence(seq)
    """

    def __init__(self, station_id: str, seq_len: int = SEQUENCE_LENGTH) -> None:
        self._station_id = station_id
        self._seq_len    = seq_len
        self._n_features = get_n_features(station_id)
        self._ring: Deque[np.ndarray] = deque(maxlen=seq_len)
        # Latest raw readings per suffix (merged across all domains)
        self._current: Dict[str, float] = {}

    def update(self, readings: Dict[str, float]) -> None:
        """Merge new sensor readings and push a snapshot to the ring buffer."""
        self._current.update(readings)
        vec = reading_to_multisensor_vector(self._current, self._station_id)
        self._ring.append(vec)

    @property
    def is_ready(self) -> bool:
        """True once enough readings have been accumulated."""
        return len(self._ring) >= self._seq_len

    def get_sequence(self) -> Optional[np.ndarray]:
        """Return the current sliding window as (T, N_FEATURES) array."""
        if not self.is_ready:
            return None
        return sequence_to_array(list(self._ring))

    def get_latest_vector(self) -> Optional[np.ndarray]:
        """Return the most recent single-step feature vector."""
        if not self._ring:
            return None
        return self._ring[-1]

    @property
    def station_id(self) -> str:
        return self._station_id

    @property
    def n_features(self) -> int:
        return self._n_features
