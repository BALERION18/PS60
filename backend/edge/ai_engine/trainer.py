"""Standalone training script for the Isolation Forest vibration model.

This module can be run directly:
    cd backend
    python -m edge.ai_engine.trainer

Or called programmatically from scripts/train_vibration_model.py.

What it does:
  1. Generates synthetic normal + anomaly data (or loads real data if provided)
  2. Trains VibrationAnomalyModel on the normal training split
  3. Evaluates on held-out normal + all anomaly types
  4. Saves the trained model + metadata sidecar to models/vibration_anomaly/

When you have real sensor data later, replace the synthetic generation
step with a call to load_real_data() below.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

# Ensure backend/ is on sys.path when run directly
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from edge.ai_engine.synthetic_data import (
    anomaly_type_labels,
    describe_dataset,
    generate_anomaly_data,
    generate_training_data,
)
from edge.ai_engine.vibration_model import VibrationAnomalyModel
from edge.ai_engine.feature_builder import FEATURE_NAMES, N_FEATURES

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Real data loader (stub — replace when real readings exist)
# ---------------------------------------------------------------------------

def load_real_data(
    csv_path: str,
) -> Optional[np.ndarray]:
    """Load real sensor readings from a CSV file.

    Expected CSV columns (in any order):
        vibration_rms, oil_pressure_bar, coolant_temp_c,
        power_output_kw, fuel_consumption_lph

    Returns:
        np.ndarray of shape (N, N_FEATURES) or None if file not found.
    """
    import csv
    from edge.ai_engine.feature_builder import reading_to_feature_vector

    p = Path(csv_path)
    if not p.exists():
        log.warning("trainer.real_data_not_found", path=csv_path)
        return None

    rows = []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                readings = {k: float(row[k]) for k in FEATURE_NAMES if k in row}
                rows.append(reading_to_feature_vector(readings))
            except (ValueError, KeyError):
                continue

    if not rows:
        log.warning("trainer.real_data_empty", path=csv_path)
        return None

    X = np.stack(rows, axis=0).astype(np.float32)
    log.info("trainer.real_data_loaded", path=csv_path, n_samples=len(X))
    return X


# ---------------------------------------------------------------------------
# Per-anomaly-type breakdown
# ---------------------------------------------------------------------------

def _print_per_type_recall(
    model: VibrationAnomalyModel,
    n_per_type: int = 200,
) -> None:
    """Print recall for each anomaly type separately."""
    from edge.ai_engine.synthetic_data import (
        _anomaly_bearing_wear,
        _anomaly_oil_pressure_drop,
        _anomaly_coolant_overtemp,
        _anomaly_power_surge,
        _anomaly_fuel_restriction,
    )
    import numpy as np

    rng = np.random.default_rng(999)
    anomaly_types = {
        "bearing_wear":      _anomaly_bearing_wear(rng, n_per_type),
        "oil_pressure_drop": _anomaly_oil_pressure_drop(rng, n_per_type),
        "coolant_overtemp":  _anomaly_coolant_overtemp(rng, n_per_type),
        "power_surge":       _anomaly_power_surge(rng, n_per_type),
        "fuel_restriction":  _anomaly_fuel_restriction(rng, n_per_type),
    }

    print("\n  PER-ANOMALY-TYPE RECALL:")
    print(f"  {'Type':<22}  {'Detected':>8}  {'Total':>6}  {'Recall':>8}")
    print(f"  {'-'*50}")
    for atype, X_anom in anomaly_types.items():
        preds = model._pipeline.predict(X_anom)   # type: ignore[union-attr]
        detected = int((preds == -1).sum())
        recall = detected / len(X_anom)
        print(f"  {atype:<22}  {detected:>8}  {len(X_anom):>6}  {recall:>7.1%}")
    print()


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------

def run_training(
    n_normal: int = 50_000,
    n_anomaly_per_type: int = 200,
    real_data_csv: Optional[str] = None,
    notes: str = "",
) -> VibrationAnomalyModel:
    """Full training pipeline: generate → train → evaluate → save.

    Args:
        n_normal:          Number of synthetic normal samples to generate.
        n_anomaly_per_type: Anomaly samples per type for validation.
        real_data_csv:     Optional path to real sensor CSV (augments synthetic data).
        notes:             Free-text notes stored in model metadata.

    Returns:
        Trained and saved VibrationAnomalyModel instance.
    """
    print("\n" + "="*60)
    print("  VAJRAX ISOLATION FOREST — VIBRATION ANOMALY MODEL")
    print("  Model: vibration_anomaly_v1")
    print("="*60)

    # ------------------------------------------------------------------
    # 1. Generate / load data
    # ------------------------------------------------------------------
    print(f"\n[1/4] Generating synthetic data (n_normal={n_normal:,})...")
    t0 = time.time()

    X_train, X_val_normal, X_val_anomaly = generate_training_data(
        n_normal=n_normal,
        n_anomaly_per_type=n_anomaly_per_type,
    )

    # Optionally augment with real data
    if real_data_csv:
        X_real = load_real_data(real_data_csv)
        if X_real is not None:
            X_train = np.concatenate([X_train, X_real], axis=0)
            print(f"     + augmented with {len(X_real):,} real samples")

    print(f"     Done in {time.time()-t0:.1f}s")
    describe_dataset(X_train,      "TRAINING SET  (normal only)")
    describe_dataset(X_val_normal, "VALIDATION SET (normal)")
    describe_dataset(X_val_anomaly,"VALIDATION SET (anomaly)")

    # ------------------------------------------------------------------
    # 2. Train
    # ------------------------------------------------------------------
    print(f"\n[2/4] Training Isolation Forest on {len(X_train):,} samples...")
    t1 = time.time()

    model = VibrationAnomalyModel()
    model.train(X_train)

    print(f"     Done in {time.time()-t1:.1f}s")

    # ------------------------------------------------------------------
    # 3. Evaluate
    # ------------------------------------------------------------------
    print("\n[3/4] Evaluating on validation sets...")
    val_scores = model.evaluate(X_val_normal, X_val_anomaly)
    _print_per_type_recall(model, n_anomaly_per_type)

    # ------------------------------------------------------------------
    # 4. Save
    # ------------------------------------------------------------------
    print("[4/4] Saving model to disk...")
    model.save(
        val_scores=val_scores,
        n_training_samples=len(X_train),
        notes=notes or f"Trained on synthetic Antarctic generator data. n_normal={len(X_train)}",
    )

    total = time.time() - t0
    print(f"\n  ✓ Training complete in {total:.1f}s")
    print(f"  ✓ Model saved: models/vibration_anomaly/vibration_anomaly_v1.pkl")
    print(f"  ✓ Anomaly recall:  {val_scores.get('recall_anomaly', 0):.1%}")
    print(f"  ✓ False pos rate:  {val_scores.get('fp_rate', 0):.1%}")
    print()

    return model


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the VajraX vibration anomaly Isolation Forest model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--n-normal", type=int, default=50_000,
        help="Number of synthetic normal samples to generate for training.",
    )
    parser.add_argument(
        "--n-anomaly", type=int, default=200,
        help="Number of anomaly validation samples per failure type.",
    )
    parser.add_argument(
        "--real-data", type=str, default=None,
        help="Path to a CSV file with real sensor readings (optional augmentation).",
    )
    parser.add_argument(
        "--notes", type=str, default="",
        help="Free-text notes to store in model metadata.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_training(
        n_normal=args.n_normal,
        n_anomaly_per_type=args.n_anomaly,
        real_data_csv=args.real_data,
        notes=args.notes,
    )
