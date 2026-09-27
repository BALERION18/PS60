"""Training entrypoint for the VajraX vibration anomaly Isolation Forest model.

Usage (run from backend/ directory):
    python -m scripts.train_vibration_model

With options:
    python -m scripts.train_vibration_model --n-normal 100000 --notes "first real run"
    python -m scripts.train_vibration_model --real-data /path/to/sensor_export.csv

With real sensor data CSV (columns: vibration_rms, oil_pressure_bar,
coolant_temp_c, power_output_kw, fuel_consumption_lph):
    python -m scripts.train_vibration_model --real-data exports/gen1_readings.csv

The trained model is saved to:
    backend/models/vibration_anomaly/vibration_anomaly_v1.pkl
    backend/models/vibration_anomaly/vibration_anomaly_v1.json  (metadata)

After training, the Edge server automatically loads it on next startup.
You can also hot-reload it without restarting — see AIEngineService.reload_model().
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on path when called as: python -m scripts.train_vibration_model
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from edge.ai_engine.trainer import _parse_args, run_training

if __name__ == "__main__":
    args = _parse_args()
    run_training(
        n_normal=args.n_normal,
        n_anomaly_per_type=args.n_anomaly,
        real_data_csv=args.real_data,
        notes=args.notes,
    )
