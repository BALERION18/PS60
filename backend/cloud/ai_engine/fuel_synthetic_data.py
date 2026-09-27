"""Synthetic Antarctic fuel consumption time-series generator.

Produces realistic multi-year daily fuel burn data for both Maitri and
Bharati stations, incorporating:

  1. SEASONAL PATTERN
     Antarctic winter (May–Aug): consumption peaks at ~1,800–2,200 L/day
     Antarctic summer (Nov–Feb): baseline ~700–1,000 L/day
     Shoulder seasons: gradual ramp up/down

  2. TEMPERATURE CORRELATION
     Each °C below 0 adds ~18–22 L/day due to extra space heating.
     Temperatures are generated from monthly climatology + daily noise.

  3. CREW VARIATION
     Station crew changes between expeditions (Oct resupply).
     Summer: 12–20 crew.  Winter: 20–38 crew.
     Each extra person adds ~45–50 L/day.

  4. WIND EFFECT
     High wind days (> 20 m/s) add ~50–150 L extra due to heat loss.

  5. GENERATOR LOAD CORRELATION
     fuel_lday ≈ gen_load_kw × 0.28 L/kWh × 24 hrs + base_heating_load

  6. REALISTIC NOISE
     Day-to-day variability: ±5–8% Gaussian noise
     Occasional anomaly days: pipe cleaning, fuel transfer, tank testing

  7. MISSING DATA GAPS
     ~2% of days have NaN (sensor fault, manual log gap)
     Prophet handles NaN natively — it skips those rows

  8. LONG-TERM TREND
     Slight upward trend ~+0.5% per year as station ages and adds equipment

Physical basis:
  - NCPOR expedition reports: Maitri consumes ~300,000–380,000 L/year
  - Bharati (newer, better insulated): ~380,000–450,000 L/year
  - Kirloskar DG sets: heat rate ~0.28 L/kWh at 80% load
  - Antarctic stations typically run 2–3 generators in parallel in winter

Usage:
    from cloud.ai_engine.fuel_synthetic_data import generate_fuel_timeseries
    df_train, df_val = generate_fuel_timeseries("maitri", years=4)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Tuple

from cloud.ai_engine.fuel_features import (
    STATION_CONSTANTS,
    REGRESSOR_COLS,
    build_prophet_df,
    _climatological_temp,
    _climatological_wind,
    _is_winter_month,
)

RNG_SEED = 77


# ---------------------------------------------------------------------------
# Core time-series generator
# ---------------------------------------------------------------------------

def generate_fuel_timeseries(
    station_id: str = "maitri",
    years: int       = 4,
    start_year: int  = 2021,
    seed: int        = RNG_SEED,
    missing_frac: float = 0.02,
) -> pd.DataFrame:
    """Generate a daily fuel consumption DataFrame.

    Args:
        station_id:   'maitri' or 'bharati'
        years:        Number of years of data to generate.
        start_year:   Calendar year to start from.
        seed:         RNG seed for reproducibility.
        missing_frac: Fraction of days to mark as NaN (sensor gaps).

    Returns:
        pd.DataFrame with columns:
            ds, y (daily_burn_litres), ambient_temp_c, crew_count,
            is_winter, wind_speed_ms, generator_load_kw
    """
    rng    = np.random.default_rng(seed)
    consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])

    # Date range
    start = pd.Timestamp(f"{start_year}-01-01")
    end   = pd.Timestamp(f"{start_year + years}-01-01")
    dates = pd.date_range(start, end, freq="D", inclusive="left")
    n     = len(dates)

    # ----------------------------------------------------------------
    # 1. Ambient temperature: climatology + daily noise
    # ----------------------------------------------------------------
    base_temps = np.array([
        _climatological_temp(d.month) for d in dates
    ], dtype=float)
    # Daily noise: autocorrelated (weather persists over days)
    temp_noise = _autocorrelated_noise(rng, n, std=3.5, phi=0.6)
    ambient_temp = base_temps + temp_noise

    # ----------------------------------------------------------------
    # 2. Wind speed: climatology + Weibull-distributed daily variation
    # ----------------------------------------------------------------
    base_wind = np.array([
        _climatological_wind(d.month) for d in dates
    ], dtype=float)
    wind_noise = rng.weibull(2.0, size=n) * 3.0 - 2.0  # right-skewed
    wind_speed = np.clip(base_wind + wind_noise, 0.0, 45.0)

    # ----------------------------------------------------------------
    # 3. Crew count: expedition-driven step changes
    #    New expedition arrives in Oct/Nov each year — crew jumps up
    #    Winter skeleton crew stays through austral winter
    # ----------------------------------------------------------------
    crew = _generate_crew_schedule(
        dates, rng, consts["crew_winter"], consts["crew_summer"]
    )

    # ----------------------------------------------------------------
    # 4. Generator load: derived from temp + crew + load pattern
    # ----------------------------------------------------------------
    gen_load = _generate_gen_load(dates, ambient_temp, crew, rng, consts)

    # ----------------------------------------------------------------
    # 5. Daily burn rate: physics-based formula + noise
    # ----------------------------------------------------------------
    # Base heating load from temperature
    heating = np.maximum(0.0, -ambient_temp) * consts["temp_coefficient"]
    # Crew load
    crew_load = (crew - 20.0) * consts["crew_coefficient"]
    # Wind load
    wind_load = np.maximum(0.0, wind_speed - 10.0) * consts["wind_coefficient"]
    # Generator fuel burn
    gen_burn = gen_load * 0.28                      # L/kWh × h=1h  (per hour)
    gen_burn_daily = gen_burn * 24.0                # × 24 hours

    # Total daily burn
    raw_burn = consts["base_burn_lday"] + heating + crew_load + wind_load
    raw_burn = np.clip(raw_burn, 300.0, 3000.0)

    # Long-term aging trend: +0.5%/year
    day_idx   = np.arange(n, dtype=float)
    trend_mul = 1.0 + day_idx / (365.25 * years) * 0.005 * years

    # Day-of-week variation: ~3% less on weekends
    dow_factor = np.where(
        pd.DatetimeIndex(dates).dayofweek >= 5,  # Sat=5, Sun=6
        0.97, 1.0
    )

    # Gaussian multiplicative noise
    noise_mul = rng.normal(1.0, 0.055, size=n)   # 5.5% daily variability

    daily_burn = raw_burn * trend_mul * dow_factor * noise_mul

    # Occasional anomaly days (fuel transfer, testing) — spike 2–4×
    n_anomaly = int(n * 0.005)
    anom_idx  = rng.choice(n, size=n_anomaly, replace=False)
    daily_burn[anom_idx] *= rng.uniform(2.0, 4.0, size=n_anomaly)

    daily_burn = np.clip(daily_burn, 200.0, 6000.0).astype(float)

    # ----------------------------------------------------------------
    # 6. Missing data gaps (~2% of days)
    # ----------------------------------------------------------------
    if missing_frac > 0:
        n_missing  = int(n * missing_frac)
        miss_idx   = rng.choice(n, size=n_missing, replace=False)
        daily_burn[miss_idx] = np.nan

    # ----------------------------------------------------------------
    # 7. Build Prophet DataFrame
    # ----------------------------------------------------------------
    df = build_prophet_df(
        dates        = dates,
        daily_burn   = daily_burn,
        ambient_temp = ambient_temp,
        crew_count   = crew,
        wind_speed   = wind_speed,
        generator_load = gen_load,
    )
    df["station_id"] = station_id
    return df


# ---------------------------------------------------------------------------
# Train / validation split
# ---------------------------------------------------------------------------

def generate_train_val_split(
    station_id: str      = "maitri",
    years: int           = 4,
    val_months: int      = 6,
    start_year: int      = 2021,
    seed: int            = RNG_SEED,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate train/val split.

    Val set = last val_months of the generated series.
    Train set = everything before.

    Returns:
        df_train, df_val — both Prophet-format DataFrames.
    """
    df = generate_fuel_timeseries(
        station_id=station_id,
        years=years,
        start_year=start_year,
        seed=seed,
    )

    # Drop NaN rows for train (Prophet can't use them in training)
    df_clean  = df.dropna(subset=["y"]).copy()
    split_idx = -val_months * 30

    df_train = df_clean.iloc[:split_idx].reset_index(drop=True)
    df_val   = df_clean.iloc[split_idx:].reset_index(drop=True)

    return df_train, df_val


def describe_timeseries(df: pd.DataFrame, name: str = "series") -> None:
    """Print summary stats for a fuel time-series DataFrame."""
    valid = df["y"].dropna()
    print("\n" + "="*60)
    print("  %s  rows=%d  valid=%d  NaN=%d" % (
        name, len(df), len(valid), df["y"].isna().sum()))
    print("  Date range: %s to %s" % (
        df["ds"].min().date(), df["ds"].max().date()))
    print("  Burn  min=%.0f  mean=%.0f  max=%.0f  std=%.0f L/day" % (
        valid.min(), valid.mean(), valid.max(), valid.std()))
    print("  Annual total ≈ %.0f kL" % (valid.mean() * 365.25 / 1000))
    # Monthly means
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["ds"]).dt.month
    monthly = df2.groupby("month")["y"].mean()
    print("  Monthly mean burn (L/day):")
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    for m, name_m in enumerate(months, 1):
        val = monthly.get(m, float("nan"))
        bar = "#" * int(val / 100) if not np.isnan(val) else ""
        print("    %s  %6.0f  %s" % (name_m, val, bar))
    print("="*60)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _autocorrelated_noise(
    rng: np.random.Generator,
    n: int,
    std: float = 3.5,
    phi: float = 0.6,
) -> np.ndarray:
    """AR(1) autocorrelated noise — weather persists for multiple days."""
    noise = np.zeros(n)
    noise[0] = rng.normal(0, std)
    for i in range(1, n):
        noise[i] = phi * noise[i-1] + rng.normal(0, std * np.sqrt(1 - phi**2))
    return noise


def _generate_crew_schedule(
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
    winter_crew: int,
    summer_crew: int,
) -> np.ndarray:
    """Generate crew count with expedition step changes."""
    crew = np.zeros(len(dates), dtype=float)
    current_crew = float(summer_crew)

    for i, d in enumerate(dates):
        # October: new expedition arrives — crew jumps to winter level
        if d.month == 10 and d.day == 1:
            current_crew = float(winter_crew) + rng.integers(-3, 4)
        # April: winter expedition leaves — skeleton crew remains
        elif d.month == 4 and d.day == 1:
            current_crew = float(summer_crew) + rng.integers(-2, 3)
        # Small daily variation (arrivals, departures of individuals)
        daily_delta = rng.choice([-1, 0, 0, 0, 1], p=[0.05, 0.7, 0.1, 0.1, 0.05])
        current_crew = float(np.clip(current_crew + daily_delta, 8, 42))
        crew[i] = current_crew

    return crew


def _generate_gen_load(
    dates: pd.DatetimeIndex,
    ambient_temp: np.ndarray,
    crew: np.ndarray,
    rng: np.random.Generator,
    consts: dict,
) -> np.ndarray:
    """Compute daily mean generator load in kW."""
    n         = len(dates)
    base_load = consts["base_burn_lday"] / 0.28 / 24.0
    temp_load = np.maximum(0.0, -ambient_temp) * 1.5
    crew_load = (crew - 20.0) * 1.8
    noise     = rng.normal(1.0, 0.04, size=n)
    gen_load  = (base_load + temp_load + crew_load) * noise
    return np.clip(gen_load, 20.0, 250.0).astype(float)
