"""Training pipeline for the Prophet fuel burn rate forecaster.

Run from backend/ directory:
    python -m cloud.ai_engine.fuel_trainer

Or via the CLI entrypoint:
    python -m scripts.train_fuel_model

What it does:
  1. Generates synthetic daily fuel time-series for specified station(s)
  2. Splits into train (last 6 months held out as val)
  3. Trains FuelForecastModel (Prophet) on the training set
  4. Evaluates on the validation set — prints MAE, MAPE, coverage
  5. Runs a sample 90-day forward forecast
  6. Saves model to models/fuel_burn_prophet_{station}/fuel_burn_prophet_{station}_v1.pkl

By default trains both Maitri and Bharati.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import structlog

_BACKEND = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from cloud.ai_engine.fuel_features import STATION_CONSTANTS
from cloud.ai_engine.fuel_model import FuelForecastModel
from cloud.ai_engine.fuel_synthetic_data import (
    describe_timeseries,
    generate_train_val_split,
)
from cloud.ai_engine.fuel_real_data import generate_train_val_split_real

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Real data loader (stub — wire in when DB exports are available)
# ---------------------------------------------------------------------------

def load_real_fuel_data(csv_path: str, station_id: str):
    """Load real daily fuel data from a CSV export.

    Expected CSV columns:
        date (YYYY-MM-DD), daily_burn_litres, ambient_temp_c,
        crew_count, wind_speed_ms, generator_load_kw

    Returns Prophet-format DataFrame or None if file not found.
    """
    import pandas as pd
    from cloud.ai_engine.fuel_features import build_prophet_df
    import numpy as np

    p = Path(csv_path)
    if not p.exists():
        log.warning("fuel_trainer.real_data_not_found", path=csv_path)
        return None

    df = pd.read_csv(p, parse_dates=["date"])
    df = df.rename(columns={"date": "ds", "daily_burn_litres": "y"})

    required = ["ds", "y"]
    if not all(c in df.columns for c in required):
        log.warning("fuel_trainer.real_data_missing_columns", path=csv_path)
        return None

    # Fill missing regressor columns with climatological defaults
    from cloud.ai_engine.fuel_features import (
        _climatological_temp, _climatological_wind, _is_winter_flag
    )
    if "ambient_temp_c" not in df.columns:
        df["ambient_temp_c"] = [_climatological_temp(d.month) for d in df["ds"]]
    if "crew_count" not in df.columns:
        consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])
        df["crew_count"] = consts["crew_winter"]
    if "wind_speed_ms" not in df.columns:
        df["wind_speed_ms"] = [_climatological_wind(d.month) for d in df["ds"]]
    if "generator_load_kw" not in df.columns:
        df["generator_load_kw"] = 100.0
    if "is_winter" not in df.columns:
        df["is_winter"] = _is_winter_flag(df["ds"]).astype(float)

    log.info("fuel_trainer.real_data_loaded",
             path=csv_path, n_rows=len(df), station_id=station_id)
    return df


# ---------------------------------------------------------------------------
# Single-station training pipeline
# ---------------------------------------------------------------------------

def train_station(
    station_id: str,
    years: int           = 4,
    val_months: int      = 6,
    real_data_csv: Optional[str] = None,
    notes: str           = "",
    sample_forecast: bool = True,
) -> FuelForecastModel:
    """Train, evaluate, and save the fuel model for one station."""

    print("\n" + "="*60)
    print("  VAJRAX PROPHET — FUEL BURN FORECASTER")
    print("  Station: %s" % station_id.upper())
    print("  Model:   fuel_burn_prophet_%s_v1" % station_id)
    print("="*60)

    # ------------------------------------------------------------------
    # 1. Generate / load data (prefer real ERA5 weather, fall back to synthetic)
    # ------------------------------------------------------------------
    t0 = time.time()

    from pathlib import Path as _Path
    weather_csv = _Path(__file__).resolve().parent.parent.parent / "data" / f"weather_{station_id}.csv"

    if weather_csv.exists():
        print("\n[1/4] Loading REAL ERA5 weather data (Open-Meteo / ECMWF)...")
        print("     Attribution: Weather data by Open-Meteo.com / ECMWF ERA5")
        df_train, df_val = generate_train_val_split_real(
            station_id = station_id,
            val_months = val_months,
        )
    else:
        print("\n[1/4] Real weather CSV not found — using synthetic data.")
        print("     Run: python -m data.fetch_weather  to download real ERA5 data.")
        df_train, df_val = generate_train_val_split(
            station_id = station_id,
            years      = years,
            val_months = val_months,
        )

    # Optionally replace training set with real fuel measurement CSV
    if real_data_csv:
        df_real = load_real_fuel_data(real_data_csv, station_id)
        if df_real is not None:
            import pandas as pd
            cutoff  = df_train["ds"].max()
            df_real_train = df_real[df_real["ds"] <= cutoff]
            if len(df_real_train) > 30:
                df_train = df_real_train
                print("     Using real fuel measurements for training (%d days)" % len(df_train))

    print("     Done in %.1fs" % (time.time() - t0))
    describe_timeseries(df_train, "TRAINING SET")
    describe_timeseries(df_val,   "VALIDATION SET")

    # ------------------------------------------------------------------
    # 2. Train
    # ------------------------------------------------------------------
    print("\n[2/4] Training Prophet on %d days..." % len(df_train))
    t1 = time.time()

    model = FuelForecastModel(station_id=station_id)
    model.train(df_train)

    print("     Done in %.1fs" % (time.time() - t1))

    # ------------------------------------------------------------------
    # 3. Evaluate
    # ------------------------------------------------------------------
    print("\n[3/4] Evaluating on %d validation days..." % len(df_val))
    val_scores = model.evaluate(df_val)

    # ------------------------------------------------------------------
    # 4. Save
    # ------------------------------------------------------------------
    print("[4/4] Saving model...")
    model.save(
        val_scores         = val_scores,
        n_training_samples = len(df_train),
        notes              = notes or (
            "Trained on %d years synthetic Antarctic fuel data for %s."
            % (years, station_id)
        ),
    )

    total = time.time() - t0
    print("\n  Model saved: "
          "models/fuel_burn_prophet_%s/fuel_burn_prophet_%s_v1.pkl"
          % (station_id, station_id))
    print("  MAE:      %.1f L/day" % val_scores.get("mae_litres", 0))
    print("  MAPE:     %.2f%%" % val_scores.get("mape_pct", 0))
    print("  Coverage: %.1f%%" % val_scores.get("coverage_90pct", 0))
    print("  Training time: %.1fs" % total)

    # ------------------------------------------------------------------
    # Sample forecast (optional)
    # ------------------------------------------------------------------
    if sample_forecast:
        _print_sample_forecast(model, station_id)

    return model


def _print_sample_forecast(model: FuelForecastModel, station_id: str) -> None:
    """Run and print a sample 90-day forecast."""
    consts = STATION_CONSTANTS.get(station_id, STATION_CONSTANTS["maitri"])
    # Use 65% of capacity as current level
    current_litres = consts["tank_capacity_litres"] * 0.65

    print("\n  SAMPLE 90-DAY FORECAST (tank at 65% = %.0f L)" % current_litres)
    fc = model.forecast(current_tank_litres=current_litres, horizon_days=90)

    print("  Risk level         : %s" % fc.risk_level)
    print("  Avg burn (7d)      : %.0f L/day" % fc.summary.avg_daily_7d)
    print("  Avg burn (30d)     : %.0f L/day" % fc.summary.avg_daily_30d)
    print("  Total (30d)        : %.0f L" % fc.summary.total_30d_litres)
    print("  Total (90d)        : %.0f L" % fc.summary.total_90d_litres)
    print("  Peak day           : %s @ %.0f L" % (
        fc.summary.peak_day_date, fc.summary.peak_day_litres))
    if fc.days_to_warning:
        print("  Days to WARNING    : %d" % fc.days_to_warning)
    else:
        print("  Days to WARNING    : > 90 days")
    if fc.days_to_critical:
        print("  Days to CRITICAL   : %d" % fc.days_to_critical)
    else:
        print("  Days to CRITICAL   : > 90 days")

    print("\n  First 14 days:")
    print("  %-12s  %-10s  %-10s  %-10s  %-8s" % (
        "Date", "Burn(L/day)", "Lower", "Upper", "Tank%"))
    print("  " + "-"*58)
    for d in fc.daily_forecast[:14]:
        print("  %-12s  %-10.0f  %-10.0f  %-10.0f  %.1f%%" % (
            d.date,
            d.predicted_burn_litres,
            d.lower_bound_litres,
            d.upper_bound_litres,
            d.tank_pct * 100,
        ))
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the VajraX Prophet fuel burn forecasting model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--station", type=str, default="both",
        help="Station to train: 'maitri', 'bharati', or 'both'",
    )
    parser.add_argument("--years",      type=int,   default=4,
                        help="Years of synthetic data to generate.")
    parser.add_argument("--val-months", type=int,   default=6,
                        help="Months to hold out for validation.")
    parser.add_argument("--real-data",  type=str,   default=None,
                        help="Path to CSV with real daily fuel data.")
    parser.add_argument("--notes",      type=str,   default="",
                        help="Notes stored in model metadata.")
    parser.add_argument("--no-forecast", action="store_true",
                        help="Skip the sample forecast printout.")
    return parser.parse_args()


def run_training(
    station: str         = "both",
    years: int           = 4,
    val_months: int      = 6,
    real_data_csv: Optional[str] = None,
    notes: str           = "",
    sample_forecast: bool = True,
) -> None:
    """Entry point for programmatic use."""
    stations = ["maitri", "bharati"] if station == "both" else [station]
    for sid in stations:
        train_station(
            station_id     = sid,
            years          = years,
            val_months     = val_months,
            real_data_csv  = real_data_csv,
            notes          = notes,
            sample_forecast= sample_forecast,
        )
    print("\nAll stations trained successfully.")


if __name__ == "__main__":
    args = _parse_args()
    run_training(
        station        = args.station,
        years          = args.years,
        val_months     = args.val_months,
        real_data_csv  = args.real_data,
        notes          = args.notes,
        sample_forecast= not args.no_forecast,
    )
