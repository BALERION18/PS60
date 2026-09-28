"""Training entrypoint for the VajraX Prophet fuel burn forecasting model.

Usage (run from backend/ directory):

    # Train both stations (default)
    python -m scripts.train_fuel_model

    # Train one station only
    python -m scripts.train_fuel_model --station maitri

    # With real data CSV
    python -m scripts.train_fuel_model --real-data exports/maitri_fuel_log.csv

    # More data, skip forecast print
    python -m scripts.train_fuel_model --years 6 --no-forecast

CSV format for --real-data:
    date (YYYY-MM-DD), daily_burn_litres, ambient_temp_c (optional),
    crew_count (optional), wind_speed_ms (optional), generator_load_kw (optional)

Trained models are saved to:
    backend/models/fuel_burn_prophet_maitri/fuel_burn_prophet_maitri_v1.pkl
    backend/models/fuel_burn_prophet_bharati/fuel_burn_prophet_bharati_v1.pkl

The cloud scheduler (APScheduler) will load these models at startup and run
them daily to update the ai_predictions table with fresh 90-day forecasts.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from cloud.ai_engine.fuel_trainer import _parse_args, run_training

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
