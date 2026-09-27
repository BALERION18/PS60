"""Feature engineering for the Prophet fuel burn rate forecaster.

Prophet works on a two-column DataFrame: ds (date) and y (target value).
Additional regressors are added as extra columns.

Target variable:
    daily_burn_litres — total diesel consumed per day (litres)

Why daily aggregation:
    Fuel sensors sample every 10 seconds at the edge but the meaningful
    forecasting signal is daily consumption, not second-by-second readings.
    Daily aggregation also smooths out short measurement noise.

Additional regressors fed to Prophet:
    ambient_temp_c       — daily mean ambient temperature
                           Strong negative correlation: colder = more heating load
    crew_count           — number of personnel on station
                           Each person adds ~40–60 L/day baseline heating+cooking
    is_winter            — binary flag (May–August = Antarctic winter)
                           Captures the systematic seasonal spike
    wind_speed_ms        — daily mean wind speed
                           High wind increases heat loss through building envelope
    generator_load_kw    — daily mean generator output
                           Direct fuel driver: burn_rate ≈ load × 0.28 L/kWh

Derived time features (added automatically by Prophet as seasonalities):
    yearly_seasonality   — Antarctic summer/winter cycle (period=365.25)
    weekly_seasonality   — Slightly lower consumption on weekends
                           (fewer labs running, lighter cooking schedule)

Station-specific constants:
    MAITRI  capacity = 165,000 L  crew range 12–30  elevation 130m
    BHARATI capacity = 250,000 L  crew range 18–38  elevation 35m (coastal)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Station physical constants
# ---------------------------------------------------------------------------

STATION_CONSTANTS: Dict[str, Dict] = {
    "maitri": {
        "tank_capacity_litres": 165_000,
        "crew_min": 12,
        "crew_max": 30,
        "crew_winter": 24,       # typical winter crew
        "crew_summer": 16,       # reduced summer crew
        "base_burn_lday": 800,   # baseline at 0°C, 20 crew
        "temp_coefficient": 18,  # extra L/day per degree below 0°C
        "crew_coefficient": 45,  # extra L/day per extra crew member
        "wind_coefficient": 4.5, # extra L/day per m/s wind
    },
    "bharati": {
        "tank_capacity_litres": 250_000,
        "crew_min": 18,
        "crew_max": 38,
        "crew_winter": 32,
        "crew_summer": 20,
        "base_burn_lday": 1100,
        "temp_coefficient": 22,
        "crew_coefficient": 50,
        "wind_coefficient": 5.0,
    },
}

# Prophet regressor column names
REGRESSOR_COLS = [
    "ambient_temp_c",
    "crew_count",
    "is_winter",
    "wind_speed_ms",
    "generator_load_kw",
]

# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------

def build_prophet_df(
    dates: pd.DatetimeIndex,
    daily_burn: np.ndarray,
    ambient_temp: np.ndarray,
    crew_count: np.ndarray,
    wind_speed: np.ndarray,
    generator_load: np.ndarray,
) -> pd.DataFrame:
    """Build a Prophet-ready DataFrame with ds, y, and all regressors.

    Args:
        dates:          DatetimeIndex of daily timestamps (UTC midnight).
        daily_burn:     Target — litres consumed per day, shape (N,).
        ambient_temp:   Daily mean ambient temperature °C, shape (N,).
        crew_count:     Personnel on station per day, shape (N,).
        wind_speed:     Daily mean wind speed m/s, shape (N,).
        generator_load: Daily mean generator output kW, shape (N,).

    Returns:
        pd.DataFrame with columns: ds, y, ambient_temp_c, crew_count,
        is_winter, wind_speed_ms, generator_load_kw
    """
    df = pd.DataFrame({
        "ds":                dates,
        "y":                 daily_burn.astype(float),
        "ambient_temp_c":    ambient_temp.astype(float),
        "crew_count":        crew_count.astype(float),
        "is_winter":         _is_winter_flag(dates).astype(float),
        "wind_speed_ms":     wind_speed.astype(float),
        "generator_load_kw": generator_load.astype(float),
    })
    return df


def build_future_df(
    last_date: pd.Timestamp,
    horizon_days: int,
    station_id: str,
    ambient_temp_forecast: Optional[np.ndarray] = None,
    crew_schedule: Optional[np.ndarray] = None,
    wind_forecast: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Build a future DataFrame for Prophet.predict().

    If forecasts for regressors are not provided, sensible seasonal
    defaults are used (daily climatology from constants).

    Args:
        last_date:             Last date in training data.
        horizon_days:          How many days forward to forecast.
        station_id:            'maitri' or 'bharati'.
        ambient_temp_forecast: Optional array of forecast temps (horizon_days,).
        crew_schedule:         Optional array of planned crew counts.
        wind_forecast:         Optional array of forecast wind speeds.

    Returns:
        pd.DataFrame ready for model.predict().
    """
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])

    # Temperature: use seasonal climatology if not provided
    if ambient_temp_forecast is not None:
        temps = ambient_temp_forecast[:horizon_days].astype(float)
    else:
        temps = np.array([
            _climatological_temp(d.month) for d in future_dates
        ], dtype=float)

    # Crew: use seasonal schedule if not provided
    if crew_schedule is not None:
        crew = crew_schedule[:horizon_days].astype(float)
    else:
        crew = np.array([
            consts["crew_winter"] if _is_winter_month(d.month)
            else consts["crew_summer"]
            for d in future_dates
        ], dtype=float)

    # Wind: use climatological mean if not provided
    if wind_forecast is not None:
        wind = wind_forecast[:horizon_days].astype(float)
    else:
        wind = np.array([
            _climatological_wind(d.month) for d in future_dates
        ], dtype=float)

    # Generator load: rough estimate from temp + crew
    gen_load = np.array([
        _estimate_gen_load(temps[i], crew[i], station_id)
        for i in range(horizon_days)
    ], dtype=float)

    return pd.DataFrame({
        "ds":                future_dates,
        "ambient_temp_c":    temps,
        "crew_count":        crew,
        "is_winter":         _is_winter_flag(future_dates).astype(float),
        "wind_speed_ms":     wind,
        "generator_load_kw": gen_load,
    })


# ---------------------------------------------------------------------------
# Fuel level depletion calculator
# ---------------------------------------------------------------------------

def burn_to_tank_level(
    current_litres: float,
    daily_burn_forecast: np.ndarray,
) -> np.ndarray:
    """Convert a daily burn forecast into cumulative tank level.

    Args:
        current_litres:       Current fuel level in litres.
        daily_burn_forecast:  Array of predicted daily consumption (L/day).

    Returns:
        Array of tank levels at end of each day, same length as forecast.
    """
    levels = np.empty(len(daily_burn_forecast), dtype=float)
    level = current_litres
    for i, burn in enumerate(daily_burn_forecast):
        level = max(0.0, level - burn)
        levels[i] = level
    return levels


def days_until_threshold(
    current_litres: float,
    daily_burn_forecast: np.ndarray,
    threshold_litres: float,
) -> Optional[int]:
    """Return the number of days until tank drops below a threshold.

    Returns None if the threshold is never reached within the forecast horizon.
    """
    level = current_litres
    for i, burn in enumerate(daily_burn_forecast):
        level -= burn
        if level <= threshold_litres:
            return i + 1
    return None


# ---------------------------------------------------------------------------
# Climatological helpers (Antarctic seasonal patterns)
# ---------------------------------------------------------------------------

def _is_winter_month(month: int) -> bool:
    """True for Antarctic winter months May–August."""
    return month in (5, 6, 7, 8)


def _is_winter_flag(dates: pd.DatetimeIndex) -> np.ndarray:
    """Boolean array: 1 for May–August, 0 otherwise."""
    return np.array([_is_winter_month(d.month) for d in dates], dtype=np.float32)


def _climatological_temp(month: int) -> float:
    """Monthly mean temperature at Maitri (°C). Source: NCPOR climatology."""
    monthly_temps = {
        1: -6.0, 2: -9.0, 3: -17.0, 4: -22.0,
        5: -26.0, 6: -28.0, 7: -30.0, 8: -29.0,
        9: -24.0, 10: -16.0, 11: -9.0, 12: -5.0,
    }
    return monthly_temps.get(month, -15.0)


def _climatological_wind(month: int) -> float:
    """Monthly mean wind speed at Maitri (m/s)."""
    monthly_wind = {
        1: 6.0, 2: 6.5, 3: 7.5, 4: 8.0,
        5: 9.0, 6: 9.5, 7: 10.0, 8: 9.5,
        9: 8.5, 10: 7.5, 11: 6.5, 12: 6.0,
    }
    return monthly_wind.get(month, 8.0)


def _estimate_gen_load(temp_c: float, crew: float, station_id: str) -> float:
    """Rough generator load estimate from temperature and crew count."""
    consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])
    base = consts["base_burn_lday"] / 0.28 / 24   # kW from base burn rate
    temp_load  = max(0.0, -temp_c) * 1.5
    crew_load  = (crew - 20) * 1.8
    return float(np.clip(base + temp_load + crew_load, 30.0, 250.0))


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def compute_burn_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:
    """Compute MAE, RMSE, MAPE for burn rate predictions."""
    mae  = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    # MAPE: skip days where true value is near zero
    mask = y_true > 50.0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) \
        if mask.sum() > 0 else float("nan")
    return {
        "mae_litres":  round(mae, 1),
        "rmse_litres": round(rmse, 1),
        "mape_pct":    round(mape, 2),
    }


def compute_coverage(
    y_true: np.ndarray,
    yhat_lower: np.ndarray,
    yhat_upper: np.ndarray,
) -> float:
    """Fraction of true values that fall inside the prediction interval."""
    inside = ((y_true >= yhat_lower) & (y_true <= yhat_upper)).mean()
    return round(float(inside) * 100, 1)
