"""Real data loader for the Prophet fuel burn forecaster.

Loads ERA5 weather data downloaded by data/fetch_weather.py and
constructs a Prophet-ready DataFrame using real temperature and wind
as regressors. Fuel burn (y) is computed via the physics model using
real weather inputs — this is the key difference from synthetic data.

Why this approach:
  - Real temperature and wind from ERA5 are the dominant drivers of
    fuel consumption at Antarctic stations
  - The physics formula (burn = base + temp_effect + wind_effect + crew_load)
    is well-established for polar diesel stations
  - This gives us 5 years of real weather-driven fuel estimates, which is
    far more representative than random synthetic weather
  - When NCPOR provides actual fuel logs, this module is the right place
    to replace the physics formula with real measured burn values

Data source:
    ERA5 reanalysis via Open-Meteo.com
    Attribution: Weather data by Open-Meteo.com / ECMWF ERA5 (CC-BY-4.0)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from cloud.ai_engine.fuel_features import (
    STATION_CONSTANTS,
    build_prophet_df,
    _is_winter_month,
)

# Path to the data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ---------------------------------------------------------------------------
# NCPOR expedition crew schedules (from published expedition reports)
# Best estimate based on NCPOR annual reports 2019-2024
# ---------------------------------------------------------------------------
CREW_SCHEDULE = {
    "maitri": {
        # (year, month): approximate crew count
        # Winter expeditions arrive Oct/Nov, leave March/April
        # Source: NCPOR expedition reports (approximate figures)
        "winter": 25,
        "summer": 15,
        "transitions": {   # month: crew count step change
            10: 25, 11: 26, 12: 24,
            1:  20,  2: 18,  3: 16,  4: 14,
            5:  24,  6: 25,  7: 26,  8: 25,
            9:  24,
        },
    },
    "bharati": {
        "winter": 33,
        "summer": 20,
        "transitions": {
            10: 33, 11: 34, 12: 32,
            1:  26,  2: 23,  3: 21,  4: 19,
            5:  32,  6: 33,  7: 34,  8: 33,
            9:  32,
        },
    },
}


def load_weather_csv(station_id: str) -> Optional[pd.DataFrame]:
    """Load the downloaded ERA5 weather CSV for a station.

    Returns None if the file hasn't been downloaded yet.
    """
    csv_path = DATA_DIR / f"weather_{station_id}.csv"
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.rename(columns={"date": "ds"})

    # Ensure required columns exist
    required = ["ds", "temp_mean", "wind_mean"]
    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Weather CSV for {station_id} missing column '{col}'. "
                f"Re-run: python -m data.fetch_weather"
            )

    return df


def _crew_for_date(date: pd.Timestamp, station_id: str) -> float:
    """Return estimated crew count for a given date."""
    sched = CREW_SCHEDULE.get(station_id, CREW_SCHEDULE["maitri"])
    transitions = sched["transitions"]
    return float(transitions.get(date.month, sched["winter"]))


def _compute_burn_from_weather(
    temp_c: float,
    wind_ms: float,
    crew: float,
    consts: dict,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Compute estimated daily fuel burn from real weather + crew.

    Physics:
        burn = base_burn
             + temp_effect  (colder = more heating load)
             + wind_effect  (higher wind = more heat loss)
             + crew_effect  (more people = more cooking/heating)
             + noise        (±5% day-to-day variability)

    Args:
        temp_c:   Real daily mean temperature (°C)
        wind_ms:  Real daily mean wind speed (m/s)
        crew:     Estimated crew count
        consts:   Station physical constants
        rng:      Optional RNG for noise injection

    Returns:
        Estimated daily fuel burn in litres.
    """
    # Temperature effect: each degree below 0°C adds heat load
    temp_effect = max(0.0, -temp_c) * consts["temp_coefficient"]

    # Wind effect: each m/s above 5 m/s base adds heat loss
    wind_effect = max(0.0, wind_ms - 5.0) * consts["wind_coefficient"]

    # Crew effect: each person above 20-person baseline
    crew_effect = (crew - 20.0) * consts["crew_coefficient"]

    total = consts["base_burn_lday"] + temp_effect + wind_effect + crew_effect

    # Add realistic ±5% noise if rng provided
    if rng is not None:
        total *= rng.normal(1.0, 0.05)

    return float(np.clip(total, 200.0, 4000.0))


def build_real_fuel_dataframe(
    station_id: str,
    seed: int = 42,
    noise_pct: float = 0.05,
) -> Optional[pd.DataFrame]:
    """Build a Prophet-ready DataFrame using real ERA5 weather.

    Args:
        station_id:  'maitri' or 'bharati'
        seed:        RNG seed for noise injection
        noise_pct:   Day-to-day variability fraction (default 5%)

    Returns:
        Prophet DataFrame with ds, y, regressors — or None if CSV not found.
    """
    weather = load_weather_csv(station_id)
    if weather is None:
        return None

    rng    = np.random.default_rng(seed)
    consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])

    n      = len(weather)
    dates  = pd.DatetimeIndex(weather["ds"])

    # Real weather inputs
    temp_mean = weather["temp_mean"].fillna(
        weather["temp_mean"].rolling(7, center=True, min_periods=1).mean()
    ).values

    wind_mean = weather["wind_mean"].fillna(
        weather["wind_mean"].rolling(7, center=True, min_periods=1).mean()
    ).values

    # Crew schedule from NCPOR expedition data
    crew = np.array([_crew_for_date(d, station_id) for d in dates], dtype=float)

    # Generator load estimate from real temp + crew
    gen_load = np.array([
        consts["base_burn_lday"] / 0.28 / 24.0
        + max(0.0, -float(temp_mean[i])) * 1.5
        + (float(crew[i]) - 20.0) * 1.8
        for i in range(n)
    ], dtype=float)
    gen_load = np.clip(gen_load, 20.0, 250.0)

    # Compute fuel burn from real weather
    daily_burn = np.array([
        _compute_burn_from_weather(
            temp_c  = float(temp_mean[i]),
            wind_ms = float(wind_mean[i]),
            crew    = float(crew[i]),
            consts  = consts,
            rng     = rng if noise_pct > 0 else None,
        )
        for i in range(n)
    ], dtype=float)

    # Introduce ~2% missing data gaps (sensor outages)
    n_missing = int(n * 0.02)
    miss_idx  = rng.choice(n, size=n_missing, replace=False)
    daily_burn[miss_idx] = np.nan

    # Build Prophet DataFrame
    df = build_prophet_df(
        dates          = dates,
        daily_burn     = daily_burn,
        ambient_temp   = temp_mean,
        crew_count     = crew,
        wind_speed     = wind_mean,
        generator_load = gen_load,
    )
    df["station_id"] = station_id

    valid = df["y"].dropna()
    print(
        "  %s: %d days  NaN=%d  burn min=%.0f mean=%.0f max=%.0f L/day  "
        "temp min=%.1f mean=%.1f max=%.1f C" % (
            station_id.upper(),
            len(df), df["y"].isna().sum(),
            valid.min(), valid.mean(), valid.max(),
            temp_mean[~np.isnan(temp_mean)].min(),
            temp_mean[~np.isnan(temp_mean)].mean(),
            temp_mean[~np.isnan(temp_mean)].max(),
        )
    )

    return df


def generate_train_val_split_real(
    station_id: str,
    val_months: int = 6,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load real weather and split into train/val.

    Falls back to synthetic data if weather CSV not available.

    Returns:
        df_train, df_val — Prophet-format DataFrames
    """
    df = build_real_fuel_dataframe(station_id=station_id, seed=seed)

    if df is None:
        print(
            f"  WARNING: Real weather data not found for {station_id}. "
            f"Falling back to synthetic. Run: python -m data.fetch_weather"
        )
        from cloud.ai_engine.fuel_synthetic_data import generate_train_val_split
        return generate_train_val_split(station_id=station_id, seed=seed)

    df_clean  = df.dropna(subset=["y"]).copy()
    split_idx = -val_months * 30

    df_train = df_clean.iloc[:split_idx].reset_index(drop=True)
    df_val   = df_clean.iloc[split_idx:].reset_index(drop=True)

    return df_train, df_val
