"""Training pipeline for the Predictive Maintenance Random Forest model.

Run from backend/ directory:
    python -m edge.ai_engine.maintenance_trainer

Or via the script entrypoint:
    python -m scripts.train_maintenance_model

What it does:
  1. Generates 20k labelled synthetic asset health samples
  2. Trains MaintenanceModel on the training split (85%)
  3. Evaluates on the held-out validation split (15%)
  4. Prints confusion matrix, per-class metrics, feature importances
  5. Saves model to models/predictive_maintenance/predictive_maintenance_v1.pkl
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

_BACKEND = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from edge.ai_engine.maintenance_features import URGENCY_CLASSES, MAINT_FEATURE_NAMES
from edge.ai_engine.maintenance_model import MaintenanceModel
from edge.ai_engine.maintenance_synthetic_data import (
    describe_dataset,
    generate_train_val_split,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Real data loader (stub — wire in when DB exports are available)
# ---------------------------------------------------------------------------

def load_real_maintenance_data(
    csv_path: str,
) -> Optional[tuple]:
    """Load real labelled maintenance data from a CSV.

    Expected CSV columns:
        runtime_hours_since_service, anomaly_score_latest, anomaly_events_7d,
        anomaly_events_30d, vibration_trend_7d, vibration_std_7d,
        oil_pressure_trend_7d, oil_pressure_drop_rate, coolant_temp_trend_7d,
        coolant_temp_max_7d, power_output_trend_7d, power_variance_7d,
        fuel_consumption_trend_7d, runtime_hours_total,
        days_since_last_maintenance, urgency_label  (NONE/LOW/MEDIUM/HIGH)

    Returns:
        (X, y) tuple or None if file not found.
    """
    import csv
    from edge.ai_engine.maintenance_features import URGENCY_TO_INT, build_feature_dict_to_vector

    p = Path(csv_path)
    if not p.exists():
        log.warning("maintenance_trainer.real_data_not_found", path=csv_path)
        return None

    rows_X, rows_y = [], []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                label = row.get("urgency_label", "").strip().upper()
                if label not in URGENCY_TO_INT:
                    continue
                features = {k: float(row[k]) for k in MAINT_FEATURE_NAMES if k in row}
                rows_X.append(build_feature_dict_to_vector(features))
                rows_y.append(URGENCY_TO_INT[label])
            except (ValueError, KeyError):
                continue

    if not rows_X:
        return None

    X = np.stack(rows_X).astype(np.float32)
    y = np.array(rows_y, dtype=np.int32)
    log.info("maintenance_trainer.real_data_loaded",
             path=csv_path, n_samples=len(X))
    return X, y


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------

def run_training(
    n_total: int         = 20_000,
    real_data_csv: Optional[str] = None,
    notes: str           = "",
) -> MaintenanceModel:
    """Full training pipeline: generate → train → evaluate → save."""
    print("\n" + "="*60)
    print("  VAJRAX RANDOM FOREST — PREDICTIVE MAINTENANCE MODEL")
    print("  Model: predictive_maintenance_v1")
    print("="*60)

    # ------------------------------------------------------------------
    # 1. Generate / load data
    # ------------------------------------------------------------------
    print(f"\n[1/4] Generating labelled data (n_total={n_total:,})...")
    t0 = time.time()

    X_train, y_train, X_val, y_val = generate_train_val_split(n_total=n_total)

    # Optionally augment with real labelled data
    if real_data_csv:
        result = load_real_maintenance_data(real_data_csv)
        if result is not None:
            X_real, y_real = result
            X_train = np.concatenate([X_train, X_real], axis=0)
            y_train = np.concatenate([y_train, y_real], axis=0)
            print(f"     + augmented with {len(X_real):,} real samples")

    print(f"     Done in {time.time()-t0:.1f}s")
    describe_dataset(X_train, y_train, "TRAINING SET")
    describe_dataset(X_val,   y_val,   "VALIDATION SET")

    # ------------------------------------------------------------------
    # 2. Train
    # ------------------------------------------------------------------
    print(f"\n[2/4] Training Random Forest on {len(X_train):,} samples...")
    t1 = time.time()
    model = MaintenanceModel()
    model.train(X_train, y_train)
    print(f"     Done in {time.time()-t1:.1f}s")

    # ------------------------------------------------------------------
    # 3. Evaluate
    # ------------------------------------------------------------------
    print("\n[3/4] Evaluating on validation set...")
    val_scores = model.evaluate(X_val, y_val)

    # ------------------------------------------------------------------
    # 4. Save
    # ------------------------------------------------------------------
    print("[4/4] Saving model to disk...")
    model.save(
        val_scores=val_scores,
        n_training_samples=len(X_train),
        notes=notes or (
            f"Trained on synthetic asset health data. "
            f"n_total={len(X_train)}. "
            f"Classes: NONE/LOW/MEDIUM/HIGH."
        ),
    )

    total = time.time() - t0
    print(f"\n  ✓ Training complete in {total:.1f}s")
    print(f"  ✓ Model saved: models/predictive_maintenance/predictive_maintenance_v1.pkl")
    print(f"  ✓ Overall accuracy:  {val_scores.get('accuracy', 0):.1%}")
    print(f"  ✓ HIGH recall:       {val_scores.get('high_recall', 0):.1%}")
    print(f"  ✓ Weighted F1:       {val_scores.get('weighted_f1', 0):.4f}")
    print()

    return model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the VajraX predictive maintenance Random Forest model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n-total", type=int, default=20_000,
                        help="Total labelled samples to generate.")
    parser.add_argument("--real-data", type=str, default=None,
                        help="Path to CSV with real labelled maintenance data.")
    parser.add_argument("--notes", type=str, default="",
                        help="Notes stored in model metadata.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_training(
        n_total=args.n_total,
        real_data_csv=args.real_data,
        notes=args.notes,
    )
