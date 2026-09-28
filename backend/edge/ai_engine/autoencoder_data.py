"""Data generator for LSTM Autoencoder training (Model 3).

Generates multi-sensor time-series sequences for both normal and
anomalous station operation.

Normal data strategy:
    Uses CMAPSS engine channels (mapped to generator sensors) combined
    with physics-based synthetic weather/environment channels. This gives
    correlated multi-sensor sequences where generator load, temperature,
    and fuel consumption move together realistically.

Anomaly data strategy:
    5 anomaly types, each affecting multiple correlated sensors:
    1. Generator overload  — power spike + fuel surge + coolant rise
    2. Air quality event   — CO/CO2 spike (correlated with each other)
    3. Bearing wear        — vibration proxy (fuel_lph irregular) + coolant rise
    4. Pressure system     — oil pressure drop + power instability
    5. Weather extreme     — temperature plunge + wind spike + load surge
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from edge.ai_engine.multi_sensor_features import (
    SEQUENCE_LENGTH,
    get_n_features,
    reading_to_multisensor_vector,
    sequence_to_array,
    MAITRI_NOMINALS,
    BHARATI_NOMINALS,
    STATION_NOMINALS,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RNG_SEED = 55


# ---------------------------------------------------------------------------
# Normal sequence generator
# ---------------------------------------------------------------------------

def _generate_normal_sequence(
    rng: np.random.Generator,
    station_id: str,
    seq_len: int,
) -> np.ndarray:
    """Generate one normal operation sequence (seq_len, N_FEATURES)."""
    nominals = STATION_NOMINALS.get(station_id, MAITRI_NOMINALS)
    frames = []

    # Slowly varying load — AR(1) process
    load = nominals.get("grid.total_load_kw", 140.0)
    temp = nominals.get("ambient_temp_c", -15.0)
    co2  = nominals.get("co2_ppm", 600.0)

    for _ in range(seq_len):
        # Correlated generator sensors
        load  = float(np.clip(load  + rng.normal(0, 2.0), 60, 220))
        fuel  = load * 0.28 / 6.0 + rng.normal(0, 0.3)
        oil   = 4.5 + rng.normal(0, 0.1)
        cool  = 82 + load * 0.06 + rng.normal(0, 1.0)
        fuel_pct = float(np.clip(nominals.get("gen1.fuel_pct", 65) + rng.normal(0, 0.05), 10, 100))

        # Weather (slowly varying)
        temp  = float(np.clip(temp + rng.normal(0, 0.5), -65, 5))
        wind  = float(np.clip(abs(rng.normal(8, 3)), 0, 50))
        pres  = float(np.clip(nominals.get("pressure_hpa", 995) + rng.normal(0, 0.5), 950, 1040))
        hum   = float(np.clip(nominals.get("humidity_pct", 60) + rng.normal(0, 1), 0, 100))

        # Environment (slowly varying)
        co2   = float(np.clip(co2 + rng.normal(0, 5), 350, 900))
        co    = float(np.clip(rng.normal(5, 1.5), 0, 30))

        if station_id == "maitri":
            readings = {
                "gen1.fuel_pct": fuel_pct,
                "gen1.power_output_kw": load,
                "gen1.fuel_consumption_lph": fuel,
                "gen1.oil_pressure_bar": oil,
                "gen1.coolant_temp_c": cool,
                "gen2.power_output_kw": load * 0.4 + rng.normal(0, 3),
                "grid.total_load_kw": load * 1.3 + rng.normal(0, 5),
                "ambient_temp_c": temp,
                "wind_speed_ms": wind,
                "pressure_hpa": pres,
                "humidity_pct": hum,
                "co2_ppm": co2,
                "co_ppm": co,
                "pm25_ugm3": float(np.clip(rng.normal(8, 2), 0, 30)),
                "seismic_magnitude": 0.0,
            }
        else:
            solar_irr = float(np.clip(rng.normal(300, 80), 0, 1000))
            readings = {
                "gen1.fuel_pct": fuel_pct,
                "gen1.power_output_kw": load,
                "gen1.fuel_consumption_lph": fuel * 1.4,
                "solar1.output_kw": solar_irr * 0.04,
                "solar1.irradiance_wm2": solar_irr,
                "grid.total_load_kw": load * 1.5 + rng.normal(0, 8),
                "ambient_temp_c": temp + 3.0,
                "wind_speed_ms": wind,
                "pressure_hpa": pres + 5,
                "humidity_pct": hum,
                "uv_index": float(np.clip(rng.normal(2.5, 1), 0, 10)),
                "co2_ppm": co2,
                "co_ppm": co,
            }

        frames.append(reading_to_multisensor_vector(readings, station_id))

    return sequence_to_array(frames)


def generate_normal_sequences(
    n_sequences: int = 5000,
    station_id: str = "maitri",
    seq_len: int = SEQUENCE_LENGTH,
    seed: int = RNG_SEED,
) -> np.ndarray:
    """Generate (n_sequences, seq_len, N_FEATURES) normal training array."""
    rng = np.random.default_rng(seed)
    seqs = [_generate_normal_sequence(rng, station_id, seq_len) for _ in range(n_sequences)]
    return np.stack(seqs, axis=0).astype(np.float32)


# ---------------------------------------------------------------------------
# Anomaly sequence generators
# ---------------------------------------------------------------------------

def _inject_anomaly(
    rng: np.random.Generator,
    seq: np.ndarray,
    station_id: str,
    anom_type: int,
) -> np.ndarray:
    """Inject an anomaly pattern into the last half of a sequence."""
    seq = seq.copy()
    n_feat = get_n_features(station_id)
    T      = seq.shape[0]
    start  = T // 2  # anomaly starts midway

    nominals = STATION_NOMINALS.get(station_id, MAITRI_NOMINALS)

    if station_id == "maitri":
        feat_idx = {
            "gen1_fuel_pct":   0, "gen1_power_kw": 1, "gen1_fuel_lph":   2,
            "gen1_oil_bar":    3, "gen1_coolant_c": 4, "gen2_power_kw":   5,
            "grid_load_kw":    6, "ambient_temp_c": 7, "wind_speed_ms":   8,
            "pressure_hpa":    9, "humidity_pct":  10, "co2_ppm":        11,
            "co_ppm":         12, "pm25_ugm3":     13, "seismic_mag":    14,
        }
    else:
        feat_idx = {
            "gen1_fuel_pct":   0, "gen1_power_kw": 1, "gen1_fuel_lph":  2,
            "solar_kw":        3, "solar_irr":     4, "grid_load_kw":   5,
            "ambient_temp_c":  6, "wind_speed_ms": 7, "pressure_hpa":   8,
            "humidity_pct":    9, "uv_index":     10, "co2_ppm":        11,
            "co_ppm":         12,
        }

    def _spike(idx, amount, noise_std=0.02):
        for t in range(start, T):
            seq[t, idx] = float(np.clip(seq[t, idx] + amount + rng.normal(0, noise_std), 0, 1))

    def _drop(idx, amount, noise_std=0.02):
        for t in range(start, T):
            seq[t, idx] = float(np.clip(seq[t, idx] - amount + rng.normal(0, noise_std), 0, 1))

    if anom_type == 0:   # Generator overload: power + fuel + coolant spike
        _spike(feat_idx.get("gen1_power_kw", 1), rng.uniform(0.25, 0.45))
        _spike(feat_idx.get("gen1_fuel_lph",  2), rng.uniform(0.20, 0.40))
        _spike(feat_idx.get("gen1_coolant_c", 4 if station_id == "maitri" else 2), rng.uniform(0.15, 0.30))
        _spike(feat_idx.get("grid_load_kw",   6 if station_id == "maitri" else 5), rng.uniform(0.20, 0.35))

    elif anom_type == 1:  # Air quality event: CO + CO2 correlated spike
        _spike(feat_idx.get("co_ppm",  12 if station_id == "maitri" else 12), rng.uniform(0.35, 0.70))
        _spike(feat_idx.get("co2_ppm", 11), rng.uniform(0.20, 0.45))
        if station_id == "maitri":
            _spike(feat_idx.get("pm25_ugm3", 13), rng.uniform(0.20, 0.40))

    elif anom_type == 2:  # Bearing/fuel line: fuel irregular + coolant rise + oil drop
        _spike(feat_idx.get("gen1_fuel_lph", 2), rng.uniform(0.15, 0.35) * rng.choice([-1, 1]))
        if station_id == "maitri":
            _drop(feat_idx.get("gen1_oil_bar", 3), rng.uniform(0.20, 0.45))
            _spike(feat_idx.get("gen1_coolant_c", 4), rng.uniform(0.18, 0.35))

    elif anom_type == 3:  # Pressure drop: oil drops + power instability
        if station_id == "maitri":
            _drop(feat_idx.get("gen1_oil_bar", 3), rng.uniform(0.30, 0.55))
        for t in range(start, T):  # noisy power
            idx_p = feat_idx.get("gen1_power_kw", 1)
            seq[t, idx_p] = float(np.clip(seq[t, idx_p] + rng.normal(0, 0.15), 0, 1))

    elif anom_type == 4:  # Weather extreme: temp plunge + wind surge + load rise
        _drop(feat_idx.get("ambient_temp_c", 7 if station_id == "maitri" else 6), rng.uniform(0.25, 0.50))
        _spike(feat_idx.get("wind_speed_ms",  8 if station_id == "maitri" else 7), rng.uniform(0.25, 0.50))
        _spike(feat_idx.get("gen1_power_kw",  1), rng.uniform(0.15, 0.30))
        _spike(feat_idx.get("grid_load_kw",   6 if station_id == "maitri" else 5), rng.uniform(0.15, 0.30))

    return seq


def generate_anomaly_sequences(
    n_per_type: int = 200,
    station_id: str = "maitri",
    seq_len: int = SEQUENCE_LENGTH,
    seed: int = RNG_SEED + 1,
) -> np.ndarray:
    """Generate anomaly sequences (5 types × n_per_type)."""
    rng = np.random.default_rng(seed)
    seqs = []
    for atype in range(5):
        for _ in range(n_per_type):
            base = _generate_normal_sequence(rng, station_id, seq_len)
            anom = _inject_anomaly(rng, base, station_id, atype)
            seqs.append(anom)
    return np.stack(seqs, axis=0).astype(np.float32)


# ---------------------------------------------------------------------------
# Train / val split
# ---------------------------------------------------------------------------

def generate_autoencoder_data(
    n_normal: int = 5000,
    n_anomaly_per_type: int = 200,
    station_id: str = "maitri",
    val_fraction: float = 0.10,
    seed: int = RNG_SEED,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate train/val splits for the LSTM Autoencoder.

    Returns:
        X_train        — normal sequences (n_train, T, N_FEATURES)
        X_val_normal   — held-out normal (n_val, T, N_FEATURES)
        X_val_anomaly  — anomaly sequences (5*n_per_type, T, N_FEATURES)
    """
    rng = np.random.default_rng(seed)

    X_normal  = generate_normal_sequences(n_normal, station_id, SEQUENCE_LENGTH, seed)
    idx       = rng.permutation(len(X_normal))
    X_normal  = X_normal[idx]
    n_val     = int(n_normal * val_fraction)
    X_val_n   = X_normal[:n_val]
    X_train   = X_normal[n_val:]
    X_val_a   = generate_anomaly_sequences(n_anomaly_per_type, station_id, SEQUENCE_LENGTH, seed + 77)

    return X_train, X_val_n, X_val_a


ANOMALY_TYPE_NAMES = [
    "generator_overload",
    "air_quality_event",
    "bearing_fuel_fault",
    "oil_pressure_drop",
    "weather_extreme",
]
