"""Predictive Maintenance Random Forest Classifier — Model 4.

Takes 15 asset-health features (runtime hours, IF anomaly score,
rolling sensor trends) and classifies maintenance urgency into:
    NONE   → healthy, no action needed
    LOW    → service approaching, plan resources
    MEDIUM → degradation detected, schedule within 2 weeks
    HIGH   → active fault or severely overdue, act immediately

Additionally outputs:
    - days_until_action:  estimated days before maintenance is required
    - confidence:         probability of the predicted class (0–1)
    - recommended_task:   human-readable task string

sklearn Pipeline used:
    StandardScaler → RandomForestClassifier

Random Forest chosen over other classifiers because:
  - Handles the class imbalance (NONE >> HIGH) well with class_weight="balanced"
  - Naturally provides feature importances (helps explain which sensor drove the alert)
  - Robust to the mixed-scale features without heavy hyperparameter tuning
  - Fast inference (< 1ms per prediction at runtime)
  - No assumption of linearity — maintenance degradation is highly non-linear

Days-until-action estimation:
    Based on predicted class and the runtime_hours_since_service feature.
    Rule-of-thumb conversion from urgency to expected days:
        HIGH   → 0–3 days
        MEDIUM → 4–14 days
        LOW    → 15–45 days
        NONE   → > 90 days
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from edge.ai_engine.maintenance_features import (
    INT_TO_URGENCY,
    MAINT_FEATURE_NAMES,
    N_MAINT_FEATURES,
    URGENCY_CLASSES,
    URGENCY_TO_INT,
    build_feature_dict_to_vector,
    build_feature_vector,
    get_task_description,
)
from edge.ai_engine.model_store import (
    ModelMetadata,
    ModelStore,
    get_model_store,
    utcnow_iso,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_NAME    = "predictive_maintenance"
MODEL_VERSION = "v1"

# Random Forest hyperparameters
RF_N_ESTIMATORS  = 300
RF_MAX_DEPTH     = None    # grow full trees — pruned implicitly by min_samples_leaf
RF_MIN_SAMPLES_LEAF = 5
RF_CLASS_WEIGHT  = "balanced_subsample"  # handles NONE >> HIGH imbalance
RF_RANDOM_STATE  = 42
RF_N_JOBS        = -1      # use all CPU cores

# Days-until-action lookup by urgency class
_DAYS_UNTIL_ACTION = {
    "HIGH":   2,
    "MEDIUM": 10,
    "LOW":    30,
    "NONE":   120,
}


# ---------------------------------------------------------------------------
# Prediction output
# ---------------------------------------------------------------------------

@dataclass
class MaintenancePrediction:
    """Result of running maintenance inference on one asset state."""
    asset_id: str
    urgency: str                        # NONE | LOW | MEDIUM | HIGH
    urgency_int: int                    # 0–3
    confidence: float                   # probability of predicted class
    days_until_action: int              # estimated days before service needed
    recommended_task: str               # human-readable action string
    class_probabilities: Dict[str, float]  # {class: probability}
    feature_importances: Dict[str, float]  # top features driving prediction
    raw_features: Dict[str, float]      # input feature dict (for logging)
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION

    @property
    def requires_action(self) -> bool:
        return self.urgency in ("LOW", "MEDIUM", "HIGH")

    @property
    def is_urgent(self) -> bool:
        return self.urgency in ("MEDIUM", "HIGH")

    def to_dict(self) -> dict:
        return {
            "asset_id":            self.asset_id,
            "urgency":             self.urgency,
            "confidence":          round(self.confidence, 4),
            "days_until_action":   self.days_until_action,
            "recommended_task":    self.recommended_task,
            "class_probabilities": {k: round(v, 4) for k, v in self.class_probabilities.items()},
            "top_features":        {k: round(v, 4) for k, v in list(self.feature_importances.items())[:5]},
            "model_name":          self.model_name,
            "model_version":       self.model_version,
        }


# ---------------------------------------------------------------------------
# Main model class
# ---------------------------------------------------------------------------

class MaintenanceModel:
    """Random Forest predictive maintenance classifier.

    Usage — training:
        model = MaintenanceModel()
        model.train(X_train, y_train)
        model.evaluate(X_val, y_val)
        model.save()

    Usage — inference:
        model = MaintenanceModel.load()
        pred = model.predict(asset_id="maitri.gen1", features={...})
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Pipeline] = None
        self._metadata: Optional[ModelMetadata] = None
        self._store: ModelStore = get_model_store()
        self._feature_importances: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = RF_N_ESTIMATORS,
    ) -> None:
        """Fit the Random Forest pipeline.

        Args:
            X_train: Feature matrix, shape (N, N_MAINT_FEATURES).
            y_train: Integer labels, shape (N,), values 0–3.
            n_estimators: Number of trees in the forest.
        """
        log.info(
            "maintenance_model.training_start",
            n_samples=len(X_train),
            n_features=X_train.shape[1],
            n_estimators=n_estimators,
            class_counts={
                URGENCY_CLASSES[i]: int((y_train == i).sum())
                for i in range(len(URGENCY_CLASSES))
            },
        )

        self._pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=RF_MAX_DEPTH,
                min_samples_leaf=RF_MIN_SAMPLES_LEAF,
                class_weight=RF_CLASS_WEIGHT,
                random_state=RF_RANDOM_STATE,
                n_jobs=RF_N_JOBS,
            )),
        ])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._pipeline.fit(X_train, y_train)

        # Cache feature importances from the RF (not from the scaler)
        self._feature_importances = self._pipeline.named_steps["rf"].feature_importances_

        log.info(
            "maintenance_model.training_done",
            n_samples=len(X_train),
            top_feature=MAINT_FEATURE_NAMES[int(np.argmax(self._feature_importances))],
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, float]:
        """Evaluate on validation set. Prints confusion matrix + per-class metrics."""
        if self._pipeline is None:
            raise RuntimeError("Model not trained.")

        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            confusion_matrix,
        )

        y_pred = self._pipeline.predict(X_val)
        acc    = accuracy_score(y_val, y_pred)
        cm     = confusion_matrix(y_val, y_pred)
        report = classification_report(
            y_val, y_pred,
            target_names=URGENCY_CLASSES,
            output_dict=True,
            zero_division=0,
        )

        # Pretty print
        print("\n" + "="*60)
        print("  PREDICTIVE MAINTENANCE MODEL — EVALUATION REPORT")
        print("="*60)
        print(f"  Overall Accuracy:  {acc:.1%}")
        print(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
        print(f"  {'':8}", end="")
        for c in URGENCY_CLASSES:
            print(f"  {c:<8}", end="")
        print()
        for i, row_label in enumerate(URGENCY_CLASSES):
            print(f"  {row_label:<8}", end="")
            for j in range(len(URGENCY_CLASSES)):
                val = cm[i][j] if i < len(cm) and j < len(cm[i]) else 0
                print(f"  {val:<8}", end="")
            print()
        print(f"\n  Per-class F1 scores:")
        for cls in URGENCY_CLASSES:
            r = report.get(cls, {})
            print(f"    {cls:<8}  precision={r.get('precision', 0):.2f}  "
                  f"recall={r.get('recall', 0):.2f}  "
                  f"f1={r.get('f1-score', 0):.2f}  "
                  f"support={int(r.get('support', 0))}")
        print(f"\n  HIGH class recall:  {report.get('HIGH', {}).get('recall', 0):.1%}  "
              f"(most safety-critical)")
        if self._feature_importances is not None:
            top_idx = np.argsort(self._feature_importances)[::-1][:5]
            print(f"\n  Top 5 feature importances:")
            for idx in top_idx:
                print(f"    {MAINT_FEATURE_NAMES[idx]:<35}  "
                      f"{self._feature_importances[idx]:.4f}")
        print("="*60 + "\n")

        metrics = {
            "accuracy":            round(float(acc), 4),
            "high_recall":         round(float(report.get("HIGH", {}).get("recall", 0)), 4),
            "high_precision":      round(float(report.get("HIGH", {}).get("precision", 0)), 4),
            "medium_recall":       round(float(report.get("MEDIUM", {}).get("recall", 0)), 4),
            "low_recall":          round(float(report.get("LOW", {}).get("recall", 0)), 4),
            "none_precision":      round(float(report.get("NONE", {}).get("precision", 0)), 4),
            "weighted_f1":         round(float(report.get("weighted avg", {}).get("f1-score", 0)), 4),
        }
        log.info("maintenance_model.evaluation", **metrics)
        return metrics

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(
        self,
        val_scores: Optional[Dict[str, float]] = None,
        n_training_samples: int = 0,
        notes: str = "",
    ) -> None:
        """Save trained model and metadata."""
        if self._pipeline is None:
            raise RuntimeError("Nothing to save — train() first.")

        metadata = ModelMetadata(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            trained_at=utcnow_iso(),
            algorithm="RandomForestClassifier",
            feature_names=MAINT_FEATURE_NAMES,
            n_features=N_MAINT_FEATURES,
            n_training_samples=n_training_samples,
            hyperparameters={
                "n_estimators":       RF_N_ESTIMATORS,
                "max_depth":          str(RF_MAX_DEPTH),
                "min_samples_leaf":   RF_MIN_SAMPLES_LEAF,
                "class_weight":       RF_CLASS_WEIGHT,
                "random_state":       RF_RANDOM_STATE,
                "urgency_classes":    URGENCY_CLASSES,
            },
            val_scores=val_scores or {},
            notes=notes,
        )
        self._metadata = metadata
        self._store.save(self._pipeline, metadata)

    @classmethod
    def load(
        cls,
        version: str = MODEL_VERSION,
        store: Optional[ModelStore] = None,
    ) -> "MaintenanceModel":
        """Load a trained model from disk."""
        _store = store or get_model_store()
        instance = cls()
        instance._store = _store
        instance._pipeline, instance._metadata = _store.load(MODEL_NAME, version)

        # Restore feature importances cache
        rf = instance._pipeline.named_steps.get("rf")
        if rf is not None and hasattr(rf, "feature_importances_"):
            instance._feature_importances = rf.feature_importances_

        log.info(
            "maintenance_model.loaded",
            version=version,
            trained_at=instance._metadata.trained_at,
        )
        return instance

    @classmethod
    def load_or_none(cls, version: str = MODEL_VERSION) -> Optional["MaintenanceModel"]:
        """Like load() but returns None instead of raising if not found."""
        try:
            return cls.load(version)
        except FileNotFoundError:
            log.warning(
                "maintenance_model.not_found",
                version=version,
                hint="Run: python -m scripts.train_maintenance_model",
            )
            return None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(
        self,
        asset_id: str,
        features: Dict[str, float],
    ) -> MaintenancePrediction:
        """Run maintenance inference from a dict of raw feature values.

        Args:
            asset_id: e.g. "maitri.gen1"
            features: dict of {feature_name: raw_value} — physical units.
                      Missing keys fall back to nominal defaults.

        Returns:
            MaintenancePrediction with urgency, confidence, recommended task.
        """
        if self._pipeline is None:
            raise RuntimeError("Model not loaded.")

        vec    = build_feature_dict_to_vector(features)
        X      = vec.reshape(1, -1)
        y_pred = int(self._pipeline.predict(X)[0])
        proba  = self._pipeline.predict_proba(X)[0]

        urgency    = INT_TO_URGENCY[y_pred]
        confidence = float(proba[y_pred])
        task       = get_task_description(urgency, features)
        days       = _estimate_days_until_action(urgency, features)

        # Feature importances (global, from the trained forest)
        fi: Dict[str, float] = {}
        if self._feature_importances is not None:
            top_idx = np.argsort(self._feature_importances)[::-1]
            fi = {
                MAINT_FEATURE_NAMES[i]: round(float(self._feature_importances[i]), 4)
                for i in top_idx
            }

        pred = MaintenancePrediction(
            asset_id=asset_id,
            urgency=urgency,
            urgency_int=y_pred,
            confidence=confidence,
            days_until_action=days,
            recommended_task=task,
            class_probabilities={
                URGENCY_CLASSES[i]: round(float(proba[i]), 4)
                for i in range(len(URGENCY_CLASSES))
            },
            feature_importances=fi,
            raw_features={k: round(v, 3) for k, v in features.items()},
        )

        if pred.is_urgent:
            log.warning(
                "maintenance_model.urgent_detected",
                asset_id=asset_id,
                urgency=urgency,
                confidence=round(confidence, 3),
                days_until_action=days,
                task=task,
            )
        elif pred.requires_action:
            log.info(
                "maintenance_model.action_recommended",
                asset_id=asset_id,
                urgency=urgency,
                days_until_action=days,
            )

        return pred

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata


# ---------------------------------------------------------------------------
# Days-until-action estimator
# ---------------------------------------------------------------------------

def _estimate_days_until_action(urgency: str, features: Dict[str, float]) -> int:
    """Refine the days estimate based on urgency + runtime hours signal."""
    base = _DAYS_UNTIL_ACTION.get(urgency, 120)
    runtime = features.get("runtime_hours_since_service", 500.0)

    if urgency == "HIGH":
        # If also severely overdue, make it 0–1 days
        if runtime > 1500:
            return 0
        return min(3, base)

    if urgency == "MEDIUM":
        # Scale by how far past 700hr threshold
        excess = max(0.0, runtime - 700.0) / 500.0  # 0–1
        return max(1, int(base - excess * 6))

    if urgency == "LOW":
        # More hours = sooner
        excess = max(0.0, runtime - 400.0) / 350.0
        return max(15, int(base - excess * 15))

    return base
