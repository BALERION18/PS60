"""Data loader for the Predictive Maintenance Random Forest (Model 4).

PRIMARY SOURCE — NASA CMAPSS FD001 (real engine degradation data):
    Loads the labeled CMAPSS dataset downloaded by data/fetch_cmapss.py.
    RUL values map directly to urgency labels:
        RUL > 120  -> NONE   (healthy)
        RUL 60-120 -> LOW    (mild wear)
        RUL 25-60  -> MEDIUM (significant degradation)
        RUL < 25   -> HIGH   (near failure)

    Feature extraction from CMAPSS per-engine trajectory:
    For each cycle we compute rolling window features (mean/std over last
    20 cycles) to get trend features, matching the AssetState accumulator
    used in production inference.

FALLBACK SOURCE — Physics-based overlapping synthetic data with noise:
    If CMAPSS CSV is not present, falls back to the v2 synthetic generator
    (with overlapping ranges, Gaussian noise, hard cases, mislabels).

Source: NASA Prognostics Center of Excellence (public domain)
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from edge.ai_engine.maintenance_features import (
    N_MAINT_FEATURES,
    URGENCY_CLASSES,
    URGENCY_TO_INT,
    build_feature_vector,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RNG_SEED = 123

# Window size for rolling trend features (cycles)
WINDOW = 20


# ---------------------------------------------------------------------------
# CMAPSS real data loader
# ---------------------------------------------------------------------------

def _load_cmapss_labeled() -> Tuple[np.ndarray, np.ndarray]:
    """Load cmapss_labeled.csv and extract maintenance features + labels.

    For each engine cycle we compute:
      - runtime_hours_since_service : cycle number (proxy for hours)
      - anomaly_score_latest        : inverted normalised vibration deviation
      - anomaly_events_7d           : rolling count of high-vibration cycles
      - anomaly_events_30d          : longer window count
      - vibration_trend_7d          : rolling mean vibration_rms
      - vibration_std_7d            : rolling std vibration_rms
      - oil_pressure_trend_7d       : rolling mean oil_pressure_bar
      - oil_pressure_drop_rate      : slope of oil pressure (bar/20 cycles)
      - coolant_temp_trend_7d       : rolling mean coolant_temp_c
      - coolant_temp_max_7d         : rolling max coolant_temp_c
      - power_output_trend_7d       : rolling mean power_output_kw
      - power_variance_7d           : rolling variance power
      - fuel_consumption_trend_7d   : rolling mean fuel_consumption_lph
      - runtime_hours_total         : max cycle for this engine (total life)
      - days_since_last_maintenance : same as runtime_hours_since_service
                                      (no maintenance events in CMAPSS)
    """
    csv_path = DATA_DIR / "cmapss_labeled.csv"
    if not csv_path.exists():
        return np.empty((0, N_MAINT_FEATURES), dtype=np.float32), np.empty(0, dtype=np.int32)

    # --- Read CSV ---
    engines: dict = {}  # engine_id -> list of rows sorted by cycle
    with open(csv_path, newline="", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        for line in f:
            vals = line.strip().split(",")
            if len(vals) < len(header):
                continue
            row = dict(zip(header, vals))
            try:
                eid  = int(float(row["engine_id"]))
                cyc  = int(float(row["cycle"]))
                rul  = int(float(row["rul"]))
                vib  = float(row.get("vibration_rms", 3.0))
                oil  = float(row.get("oil_pressure_bar", 4.5))
                cool = float(row.get("coolant_temp_c", 85.0))
                pwr  = float(row.get("power_output_kw", 100.0))
                fuel = float(row.get("fuel_consumption_lph", 15.0))
                urg  = row.get("urgency_label", "NONE").strip()
            except (ValueError, KeyError):
                continue

            if eid not in engines:
                engines[eid] = []
            engines[eid].append({
                "cycle": cyc, "rul": rul,
                "vibration_rms": vib, "oil_pressure_bar": oil,
                "coolant_temp_c": cool, "power_output_kw": pwr,
                "fuel_consumption_lph": fuel,
                "urgency_label": urg,
            })

    # Sort each engine by cycle
    for eid in engines:
        engines[eid].sort(key=lambda r: r["cycle"])

    # --- Feature extraction with rolling windows ---
    X_rows, y_rows = [], []

    for eid, rows in engines.items():
        n = len(rows)
        max_cycle = rows[-1]["cycle"]

        vibs  = [r["vibration_rms"]    for r in rows]
        oils  = [r["oil_pressure_bar"] for r in rows]
        cools = [r["coolant_temp_c"]   for r in rows]
        pwrs  = [r["power_output_kw"]  for r in rows]
        fuels = [r["fuel_consumption_lph"] for r in rows]

        # Anomaly threshold: vibration > mean + 2std is an "event"
        vib_arr   = np.array(vibs)
        vib_mean  = vib_arr.mean()
        vib_std   = vib_arr.std() + 1e-6
        anom_flags = (vib_arr > vib_mean + 1.5 * vib_std).astype(float)

        for i, row in enumerate(rows):
            w_start = max(0, i - WINDOW)
            w_slice = slice(w_start, i + 1)

            vib_win  = vibs[w_slice.start:w_slice.stop]
            oil_win  = oils[w_slice.start:w_slice.stop]
            cool_win = cools[w_slice.start:w_slice.stop]
            pwr_win  = pwrs[w_slice.start:w_slice.stop]
            fuel_win = fuels[w_slice.start:w_slice.stop]
            anom_win = list(anom_flags[w_slice.start:w_slice.stop])

            # Oil pressure drop rate (slope over window, normalised to bar/day)
            if len(oil_win) > 3:
                x_idx  = np.arange(len(oil_win), dtype=float)
                slope  = float(np.polyfit(x_idx, oil_win, 1)[0])
                oil_drop_rate = max(0.0, -slope * 8.0)  # per-cycle -> per-day estimate
            else:
                oil_drop_rate = 0.0

            # IF anomaly score proxy: deviation from healthy baseline
            vib_now  = row["vibration_rms"]
            if_score_proxy = float(np.clip(
                0.1 - (vib_now - vib_mean) / (vib_std * 3.0),
                -0.25, 0.15
            ))

            feat_vec = build_feature_vector(
                runtime_hours_since_service = float(row["cycle"]),
                anomaly_score_latest        = if_score_proxy,
                anomaly_events_7d           = int(sum(anom_win[-7:])),
                anomaly_events_30d          = int(sum(anom_win)),
                vibration_trend_7d          = float(np.mean(vib_win[-7:])) if len(vib_win) >= 7 else float(np.mean(vib_win)),
                vibration_std_7d            = float(np.std(vib_win[-7:])) if len(vib_win) >= 7 else float(np.std(vib_win)) + 0.1,
                oil_pressure_trend_7d       = float(np.mean(oil_win[-7:])) if len(oil_win) >= 7 else float(np.mean(oil_win)),
                oil_pressure_drop_rate      = oil_drop_rate,
                coolant_temp_trend_7d       = float(np.mean(cool_win[-7:])) if len(cool_win) >= 7 else float(np.mean(cool_win)),
                coolant_temp_max_7d         = float(max(cool_win[-7:])) if len(cool_win) >= 7 else float(max(cool_win)),
                power_output_trend_7d       = float(np.mean(pwr_win[-7:])) if len(pwr_win) >= 7 else float(np.mean(pwr_win)),
                power_variance_7d           = float(np.var(pwr_win[-7:])) if len(pwr_win) >= 7 else float(np.var(pwr_win)) + 1.0,
                fuel_consumption_trend_7d   = float(np.mean(fuel_win[-7:])) if len(fuel_win) >= 7 else float(np.mean(fuel_win)),
                runtime_hours_total         = float(max_cycle),
                days_since_last_maintenance = float(row["cycle"]),
            )

            label_str = row["urgency_label"]
            label_int = URGENCY_TO_INT.get(label_str, 0)

            X_rows.append(feat_vec)
            y_rows.append(label_int)

    if not X_rows:
        return np.empty((0, N_MAINT_FEATURES), dtype=np.float32), np.empty(0, dtype=np.int32)

    X = np.stack(X_rows, axis=0).astype(np.float32)
    y = np.array(y_rows, dtype=np.int32)
    return X, y


# ---------------------------------------------------------------------------
# Synthetic fallback (v2 — with overlap, noise, hard cases)
# ---------------------------------------------------------------------------

DEFAULT_NOISE_STD     = 0.04
HARD_CASE_FRACTION    = 0.08
MISLABEL_FRACTION     = 0.02


def _add_noise(X: np.ndarray, rng: np.random.Generator, std: float = DEFAULT_NOISE_STD) -> np.ndarray:
    return np.clip(X + rng.normal(0.0, std, size=X.shape).astype(np.float32), 0.0, 1.0)


def _apply_mislabels(y: np.ndarray, rng: np.random.Generator, fraction: float = MISLABEL_FRACTION) -> np.ndarray:
    y = y.copy()
    idx = rng.choice(len(y), size=int(len(y) * fraction), replace=False)
    for i in idx:
        y[i] = int(np.clip(y[i] + rng.choice([-1, 1]), 0, 3))
    return y


def _sample_none(rng, n):
    rows = []
    for _ in range(n):
        rows.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(0, 500), anomaly_score_latest=rng.uniform(0.02, 0.22),
            anomaly_events_7d=int(rng.integers(0, 3)), anomaly_events_30d=int(rng.integers(0, 6)),
            vibration_trend_7d=rng.uniform(1.5, 6.5), vibration_std_7d=rng.uniform(0.2, 1.2),
            oil_pressure_trend_7d=rng.uniform(3.8, 5.5), oil_pressure_drop_rate=rng.uniform(0.0, 0.08),
            coolant_temp_trend_7d=rng.uniform(76, 96), coolant_temp_max_7d=rng.uniform(86, 100),
            power_output_trend_7d=rng.uniform(50, 140), power_variance_7d=rng.uniform(15, 350),
            fuel_consumption_trend_7d=rng.uniform(9, 26), runtime_hours_total=rng.uniform(200, 18000),
            days_since_last_maintenance=rng.uniform(0, 75),
        ))
    return np.stack(rows).astype(np.float32)


def _sample_low(rng, n):
    rows = []
    for _ in range(n):
        rows.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(350, 850), anomaly_score_latest=rng.uniform(-0.04, 0.06),
            anomaly_events_7d=int(rng.integers(1, 6)), anomaly_events_30d=int(rng.integers(2, 14)),
            vibration_trend_7d=rng.uniform(4.0, 9.5), vibration_std_7d=rng.uniform(0.5, 2.0),
            oil_pressure_trend_7d=rng.uniform(3.2, 4.5), oil_pressure_drop_rate=rng.uniform(0.03, 0.18),
            coolant_temp_trend_7d=rng.uniform(88, 104), coolant_temp_max_7d=rng.uniform(94, 108),
            power_output_trend_7d=rng.uniform(55, 135), power_variance_7d=rng.uniform(100, 800),
            fuel_consumption_trend_7d=rng.uniform(13, 28), runtime_hours_total=rng.uniform(800, 28000),
            days_since_last_maintenance=rng.uniform(50, 140),
        ))
    return np.stack(rows).astype(np.float32)


def _sample_medium(rng, n):
    rows = []
    for _ in range(n):
        rows.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(700, 1300), anomaly_score_latest=rng.uniform(-0.10, -0.01),
            anomaly_events_7d=int(rng.integers(3, 12)), anomaly_events_30d=int(rng.integers(7, 30)),
            vibration_trend_7d=rng.uniform(6.5, 15.0), vibration_std_7d=rng.uniform(1.0, 4.0),
            oil_pressure_trend_7d=rng.uniform(2.5, 3.8), oil_pressure_drop_rate=rng.uniform(0.08, 0.40),
            coolant_temp_trend_7d=rng.uniform(96, 110), coolant_temp_max_7d=rng.uniform(101, 114),
            power_output_trend_7d=rng.uniform(45, 135), power_variance_7d=rng.uniform(300, 1500),
            fuel_consumption_trend_7d=rng.uniform(16, 36), runtime_hours_total=rng.uniform(1500, 38000),
            days_since_last_maintenance=rng.uniform(100, 220),
        ))
    return np.stack(rows).astype(np.float32)


def _sample_high(rng, n):
    rows = []
    for _ in range(n):
        mode = rng.integers(0, 4)
        base = dict(
            runtime_hours_since_service=rng.uniform(1100, 2000), anomaly_score_latest=rng.uniform(-0.22, -0.06),
            anomaly_events_7d=int(rng.integers(7, 20)), anomaly_events_30d=int(rng.integers(18, 60)),
            vibration_trend_7d=rng.uniform(4.0, 12.0), vibration_std_7d=rng.uniform(0.5, 3.0),
            oil_pressure_trend_7d=rng.uniform(2.8, 4.5), oil_pressure_drop_rate=rng.uniform(0.04, 0.25),
            coolant_temp_trend_7d=rng.uniform(84, 100), coolant_temp_max_7d=rng.uniform(90, 104),
            power_output_trend_7d=rng.uniform(35, 135), power_variance_7d=rng.uniform(150, 1000),
            fuel_consumption_trend_7d=rng.uniform(11, 28), runtime_hours_total=rng.uniform(2500, 50000),
            days_since_last_maintenance=rng.uniform(160, 400),
        )
        if mode == 0:
            base["vibration_trend_7d"] = rng.uniform(13.0, 25.0)
            base["vibration_std_7d"]   = rng.uniform(3.0, 7.0)
        elif mode == 1:
            base["oil_pressure_trend_7d"]  = rng.uniform(0.8, 2.5)
            base["oil_pressure_drop_rate"] = rng.uniform(0.30, 1.50)
        elif mode == 2:
            base["coolant_temp_trend_7d"] = rng.uniform(106, 118)
            base["coolant_temp_max_7d"]   = rng.uniform(112, 120)
        else:
            base["runtime_hours_since_service"] = rng.uniform(1500, 2000)
            base["days_since_last_maintenance"]  = rng.uniform(300, 730)
        rows.append(build_feature_vector(**base))
    return np.stack(rows).astype(np.float32)


def _sample_hard_cases(rng, n):
    n_per_zone = n // 3
    remainder  = n - n_per_zone * 3
    rows_X, rows_y = [], []
    for _ in range(n_per_zone):
        rows_X.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(380, 520), anomaly_score_latest=rng.uniform(-0.01, 0.03),
            anomaly_events_7d=int(rng.integers(1, 3)), anomaly_events_30d=int(rng.integers(2, 7)),
            vibration_trend_7d=rng.uniform(4.8, 6.5), vibration_std_7d=rng.uniform(0.7, 1.3),
            oil_pressure_trend_7d=rng.uniform(3.7, 4.3), oil_pressure_drop_rate=rng.uniform(0.04, 0.10),
            coolant_temp_trend_7d=rng.uniform(90, 97), coolant_temp_max_7d=rng.uniform(95, 102),
            power_output_trend_7d=rng.uniform(70, 120), power_variance_7d=rng.uniform(150, 400),
            fuel_consumption_trend_7d=rng.uniform(14, 22), runtime_hours_total=rng.uniform(2000, 20000),
            days_since_last_maintenance=rng.uniform(55, 80),
        ))
        rows_y.append(URGENCY_TO_INT["LOW"])
    for _ in range(n_per_zone):
        rows_X.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(720, 880), anomaly_score_latest=rng.uniform(-0.05, -0.01),
            anomaly_events_7d=int(rng.integers(3, 7)), anomaly_events_30d=int(rng.integers(10, 20)),
            vibration_trend_7d=rng.uniform(7.5, 10.5), vibration_std_7d=rng.uniform(1.3, 2.5),
            oil_pressure_trend_7d=rng.uniform(3.0, 3.7), oil_pressure_drop_rate=rng.uniform(0.10, 0.22),
            coolant_temp_trend_7d=rng.uniform(99, 106), coolant_temp_max_7d=rng.uniform(104, 110),
            power_output_trend_7d=rng.uniform(60, 125), power_variance_7d=rng.uniform(350, 800),
            fuel_consumption_trend_7d=rng.uniform(17, 27), runtime_hours_total=rng.uniform(3000, 30000),
            days_since_last_maintenance=rng.uniform(110, 155),
        ))
        rows_y.append(URGENCY_TO_INT["MEDIUM"])
    for _ in range(n_per_zone + remainder):
        rows_X.append(build_feature_vector(
            runtime_hours_since_service=rng.uniform(1050, 1350), anomaly_score_latest=rng.uniform(-0.10, -0.05),
            anomaly_events_7d=int(rng.integers(7, 12)), anomaly_events_30d=int(rng.integers(18, 32)),
            vibration_trend_7d=rng.uniform(11.0, 16.0), vibration_std_7d=rng.uniform(2.0, 4.5),
            oil_pressure_trend_7d=rng.uniform(2.6, 3.3), oil_pressure_drop_rate=rng.uniform(0.22, 0.45),
            coolant_temp_trend_7d=rng.uniform(103, 110), coolant_temp_max_7d=rng.uniform(108, 115),
            power_output_trend_7d=rng.uniform(50, 120), power_variance_7d=rng.uniform(600, 1400),
            fuel_consumption_trend_7d=rng.uniform(20, 34), runtime_hours_total=rng.uniform(5000, 40000),
            days_since_last_maintenance=rng.uniform(165, 230),
        ))
        rows_y.append(URGENCY_TO_INT["HIGH"])
    return np.stack(rows_X).astype(np.float32), np.array(rows_y, dtype=np.int32)


def generate_maintenance_data(
    n_total: int = 20_000,
    seed: int = RNG_SEED,
    noise_std: float = DEFAULT_NOISE_STD,
    hard_case_frac: float = HARD_CASE_FRACTION,
    mislabel_frac: float = MISLABEL_FRACTION,
) -> Tuple[np.ndarray, np.ndarray]:
    """Synthetic maintenance dataset (v2 with overlap and noise). Fallback only."""
    rng   = np.random.default_rng(seed)
    n_hard   = int(n_total * hard_case_frac)
    n_core   = n_total - n_hard
    n_none   = int(n_core * 0.50)
    n_low    = int(n_core * 0.25)
    n_medium = int(n_core * 0.15)
    n_high   = n_core - n_none - n_low - n_medium

    X_core = np.concatenate([
        _sample_none(rng, n_none), _sample_low(rng, n_low),
        _sample_medium(rng, n_medium), _sample_high(rng, n_high),
    ])
    y_core = np.concatenate([
        np.full(n_none, URGENCY_TO_INT["NONE"], dtype=np.int32),
        np.full(n_low,  URGENCY_TO_INT["LOW"],  dtype=np.int32),
        np.full(n_medium, URGENCY_TO_INT["MEDIUM"], dtype=np.int32),
        np.full(n_high, URGENCY_TO_INT["HIGH"],  dtype=np.int32),
    ])
    X_hard, y_hard = _sample_hard_cases(rng, n_hard)
    X = np.concatenate([X_core, X_hard])
    y = np.concatenate([y_core, y_hard])
    if noise_std > 0:
        X = _add_noise(X, rng, std=noise_std)
    if mislabel_frac > 0:
        y = _apply_mislabels(y, rng, fraction=mislabel_frac)
    idx = rng.permutation(len(X))
    return X[idx].astype(np.float32), y[idx]


# ---------------------------------------------------------------------------
# Main split function — prefers CMAPSS, falls back to synthetic
# ---------------------------------------------------------------------------

def generate_train_val_split(
    n_total: int = 20_000,
    val_fraction: float = 0.15,
    seed: int = RNG_SEED,
    noise_std: float = DEFAULT_NOISE_STD,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate train/val split, preferring real CMAPSS data.

    Returns:
        X_train, y_train, X_val, y_val
    """
    rng = np.random.default_rng(seed)

    # Try CMAPSS first
    X_cmapss, y_cmapss = _load_cmapss_labeled()

    if len(X_cmapss) > 1000:
        print("  Using real NASA CMAPSS FD001 data for Model 4 training.")
        print("  Attribution: NASA C-MAPSS dataset (public domain, NASA Ames)")

        # Print class distribution
        total = len(y_cmapss)
        for i, cls in enumerate(URGENCY_CLASSES):
            n = int((y_cmapss == i).sum())
            print("    %-8s  %6d  (%.0f%%)" % (cls, n, n / total * 100))

        # Shuffle
        idx = rng.permutation(total)
        X_cmapss, y_cmapss = X_cmapss[idx], y_cmapss[idx]

        n_val    = int(total * val_fraction)
        X_train  = X_cmapss[n_val:]
        y_train  = y_cmapss[n_val:]
        X_val    = X_cmapss[:n_val]
        y_val    = y_cmapss[:n_val]
        return X_train, y_train, X_val, y_val

    # Fallback
    print("  CMAPSS data not found — using synthetic fallback.")
    print("  Run: python -m data.fetch_cmapss  to download real data.")
    X, y = generate_maintenance_data(n_total=n_total, seed=seed, noise_std=noise_std)
    n_val = int(len(X) * val_fraction)
    return X[n_val:], y[n_val:], X[:n_val], y[:n_val]


def describe_dataset(X: np.ndarray, y: np.ndarray, name: str = "dataset") -> None:
    """Print class distribution."""
    print("\n" + "="*60)
    print("  %s  shape=%s" % (name, X.shape))
    total = len(y)
    for i, cls in enumerate(URGENCY_CLASSES):
        count = int((y == i).sum())
        print("    %-8s  %5d  (%.0f%%)" % (cls, count, count / total * 100))
    print("="*60)
