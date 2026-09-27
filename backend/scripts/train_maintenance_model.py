"""Training entrypoint for the VajraX predictive maintenance Random Forest model.

Usage (run from backend/ directory):
    python -m scripts.train_maintenance_model

With options:
    python -m scripts.train_maintenance_model --n-total 40000
    python -m scripts.train_maintenance_model --real-data exports/maintenance_log.csv

The trained model is saved to:
    backend/models/predictive_maintenance/predictive_maintenance_v1.pkl
    backend/models/predictive_maintenance/predictive_maintenance_v1.json

After training, the Edge AI Engine service automatically loads both
Model 2 (Isolation Forest) and Model 4 (Maintenance) on next startup.
Maintenance predictions are triggered whenever Model 2 detects an anomaly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from edge.ai_engine.maintenance_trainer import _parse_args, run_training

if __name__ == "__main__":
    args = _parse_args()
    run_training(
        n_total=args.n_total,
        real_data_csv=args.real_data,
        notes=args.notes,
    )
