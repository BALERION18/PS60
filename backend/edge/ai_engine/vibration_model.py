"""Isolation Forest vibration anomaly detector.

This is the core ML model for Model 2.  It wraps sklearn's IsolationForest
in a clean interface that:

  - Trains on normal generator sensor data
  - Evaluates on validation splits and logs detection metrics
  - Maps raw anomaly scores to NOMINAL / WARNING / CRITICAL risk levels
  - Exposes a single predict() method for the inference path

Score interpretation:
    IsolationForest.decision_function() returns a score in roughly [-0.5, 0.5]:
      > 0     → more normal than average (deeply inside the normal cluster)
      ≈ 0     → boundary
      < 0     → anomalous (isolated quickly by random partitioning)
      << -0.2 → strongly anomalous

We define three risk bands from these scores:
    NOMINAL  : score >= -0.05   (well within normal distribution)
    WARNING  : -0.15 <= score < -0.05
    CRITICAL : score < -0.15

These thresholds were chosen by inspecting the validation set recall
across anomaly types.  You can retune them by calling
VibrationAnomalyModel.tune_thresholds() on a labelled validation set.

sklearn Pipeline used:
    StandardScaler → IsolationForest
The scaler is important: even though features are normalised to [0,1]
by feature_builder, their variances differ; scaling makes the IF work
uniformly across all features.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from edge.ai_engine.feature_builder import (
    FEATURE_NAMES,
    N_FEATURES,
    reading_to_feature_vector,
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
MODEL_NAME    = "vibration_anomaly"
MODEL_VERSION = "v1"

# Anomaly score thresholds (decision_function output)
THRESHOLD_WARNING  = 0.02    # score below this → WARNING  (tuned on score distribution)
THRESHOLD_CRITICAL = -0.04   # score below this → CRITICAL

# IsolationForest hyperparameters
IF_N_ESTIMATORS  = 200       # more trees → more stable scores
IF_CONTAMINATION = 0.05      # bumped from 0.02 → better sensitivity on edge cases
IF_MAX_SAMPLES   = "auto"    # "auto" = min(256, n_samples)
IF_MAX_FEATURES  = 1.0       # use all features
IF_RANDOM_STATE  = 42


# ---------------------------------------------------------------------------
# Prediction output
# ---------------------------------------------------------------------------

@dataclass
class AnomalyPrediction:
    """Result of running inference on one feature vector."""
    asset_id: str
    sensor_readings: Dict[str, float]     # raw values that triggered this
    anomaly_score: float                   # decision_function output (lower = worse)
    risk_level: str                        # NOMINAL | WARNING | CRITICAL
    is_anomaly: bool                       # True if WARNING or CRITICAL
    confidence: float                      # 0–1, derived from score
    feature_vector: List[float]            # normalised input vector
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION

    def to_dict(self) -> dict:
        return {
            "asset_id":        self.asset_id,
            "anomaly_score":   round(self.anomaly_score, 4),
            "risk_level":      self.risk_level,
            "is_anomaly":      self.is_anomaly,
            "confidence":      round(self.confidence, 4),
            "model_name":      self.model_name,
            "model_version":   self.model_version,
            "sensor_readings": {k: round(v, 3) for k, v in self.sensor_readings.items()},
        }


# ---------------------------------------------------------------------------
# Score → risk mapping
# ---------------------------------------------------------------------------

def score_to_risk_level(score: float) -> str:
    """Map an IsolationForest decision_function score to a risk label."""
    if score < THRESHOLD_CRITICAL:
        return "CRITICAL"
    if score < THRESHOLD_WARNING:
        return "WARNING"
    return "NOMINAL"


def score_to_confidence(score: float) -> float:
    """Convert anomaly score to a 0–1 confidence value.

    Maps the score range [-0.5, 0.5] linearly to [1.0, 0.0].
    A score of -0.5 (most anomalous) → confidence 1.0 that it IS an anomaly.
    A score of +0.5 (most normal)    → confidence 0.0 that it is an anomaly.
    """
    # Invert: high confidence means high anomaly-ness
    raw = (-score + 0.5)          # shift so -0.5 → 1.0, +0.5 → 0.0
    return float(np.clip(raw, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Model class
# ---------------------------------------------------------------------------

class VibrationAnomalyModel:
    """Isolation Forest anomaly detector for generator sensor data.

    Typical usage:
        # Training
        model = VibrationAnomalyModel()
        model.train(X_train)
        model.evaluate(X_val_normal, X_val_anomaly)
        model.save()

        # Inference (loaded from disk)
        model = VibrationAnomalyModel.load()
        pred = model.predict(asset_id="maitri.gen1", readings={"vibration_rms": 14.5, ...})
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Pipeline] = None
        self._metadata: Optional[ModelMetadata] = None
        self._store: ModelStore = get_model_store()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        X_train: np.ndarray,
        n_estimators: int  = IF_N_ESTIMATORS,
        contamination: float = IF_CONTAMINATION,
    ) -> None:
        """Fit the Isolation Forest pipeline on normal training data.

        Args:
            X_train:       Feature matrix of NORMAL samples, shape (N, N_FEATURES).
            n_estimators:  Number of base estimators (trees).
            contamination: Expected fraction of outliers in training data.
        """
        log.info(
            "vibration_model.training_start",
            n_samples=len(X_train),
            n_features=X_train.shape[1],
            n_estimators=n_estimators,
            contamination=contamination,
        )

        self._pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("iforest", IsolationForest(
                n_estimators=n_estimators,
                contamination=contamination,
                max_samples=IF_MAX_SAMPLES,
                max_features=IF_MAX_FEATURES,
                random_state=IF_RANDOM_STATE,
                n_jobs=-1,
            )),
        ])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._pipeline.fit(X_train)

        log.info("vibration_model.training_done", n_samples=len(X_train))

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        X_val_normal: np.ndarray,
        X_val_anomaly: np.ndarray,
    ) -> Dict[str, float]:
        """Evaluate model on held-out normal and anomaly validation sets.

        Returns a dict of metrics that gets stored in model metadata.
        Prints a human-readable report.
        """
        if self._pipeline is None:
            raise RuntimeError("Model not trained yet — call train() first.")

        # Scores: negative = anomaly, positive = normal
        scores_normal  = self._pipeline.decision_function(X_val_normal)
        scores_anomaly = self._pipeline.decision_function(X_val_anomaly)

        # Binary predictions using sklearn's built-in threshold
        preds_normal  = self._pipeline.predict(X_val_normal)   # +1 normal, -1 anomaly
        preds_anomaly = self._pipeline.predict(X_val_anomaly)

        # True positives: anomalies correctly flagged as -1
        tp = int((preds_anomaly == -1).sum())
        fn = int((preds_anomaly ==  1).sum())
        fp = int((preds_normal  == -1).sum())
        tn = int((preds_normal  ==  1).sum())

        recall_anomaly   = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision_anomaly = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        specificity       = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1 = (
            2 * precision_anomaly * recall_anomaly
            / (precision_anomaly + recall_anomaly)
            if (precision_anomaly + recall_anomaly) > 0
            else 0.0
        )

        metrics = {
            "recall_anomaly":    round(recall_anomaly, 4),
            "precision_anomaly": round(precision_anomaly, 4),
            "specificity":       round(specificity, 4),
            "f1_score":          round(f1, 4),
            "fp_rate":           round(1 - specificity, 4),
            "mean_score_normal":  round(float(scores_normal.mean()), 4),
            "mean_score_anomaly": round(float(scores_anomaly.mean()), 4),
            "n_val_normal":       len(X_val_normal),
            "n_val_anomaly":      len(X_val_anomaly),
        }

        # Pretty print
        print("\n" + "="*60)
        print("  VIBRATION ANOMALY MODEL — EVALUATION REPORT")
        print("="*60)
        print(f"  Validation normal samples : {len(X_val_normal)}")
        print(f"  Validation anomaly samples: {len(X_val_anomaly)}")
        print(f"  TP={tp}  FN={fn}  FP={fp}  TN={tn}")
        print(f"  Recall (anomaly detection): {recall_anomaly:.1%}")
        print(f"  Precision:                  {precision_anomaly:.1%}")
        print(f"  Specificity (normal kept):  {specificity:.1%}")
        print(f"  F1 Score:                   {f1:.4f}")
        print(f"  False positive rate:        {1-specificity:.1%}")
        print(f"  Mean score — normal :       {scores_normal.mean():.4f}")
        print(f"  Mean score — anomaly:       {scores_anomaly.mean():.4f}")
        print("="*60 + "\n")

        log.info("vibration_model.evaluation", **{k: v for k, v in metrics.items()
                                                   if isinstance(v, float)})
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
        """Persist the trained model and metadata to the model store."""
        if self._pipeline is None:
            raise RuntimeError("Nothing to save — train() first.")

        metadata = ModelMetadata(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            trained_at=utcnow_iso(),
            algorithm="IsolationForest",
            feature_names=FEATURE_NAMES,
            n_features=N_FEATURES,
            n_training_samples=n_training_samples,
            hyperparameters={
                "n_estimators":  IF_N_ESTIMATORS,
                "contamination": IF_CONTAMINATION,
                "max_samples":   IF_MAX_SAMPLES,
                "max_features":  IF_MAX_FEATURES,
                "random_state":  IF_RANDOM_STATE,
                "threshold_warning":  THRESHOLD_WARNING,
                "threshold_critical": THRESHOLD_CRITICAL,
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
    ) -> "VibrationAnomalyModel":
        """Load a trained model from the model store.

        Args:
            version: Model version string, e.g. "v1".
            store:   Optional custom ModelStore. Defaults to get_model_store().

        Raises:
            FileNotFoundError: if the model hasn't been trained yet.
        """
        _store = store or get_model_store()
        instance = cls()
        instance._store = _store
        instance._pipeline, instance._metadata = _store.load(MODEL_NAME, version)
        log.info(
            "vibration_model.loaded",
            version=version,
            trained_at=instance._metadata.trained_at,
        )
        return instance

    @classmethod
    def load_or_none(cls, version: str = MODEL_VERSION) -> Optional["VibrationAnomalyModel"]:
        """Like load() but returns None instead of raising if not found."""
        try:
            return cls.load(version)
        except FileNotFoundError:
            log.warning(
                "vibration_model.not_found",
                version=version,
                hint="Run: python -m scripts.train_vibration_model",
            )
            return None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(
        self,
        asset_id: str,
        readings: Dict[str, float],
    ) -> AnomalyPrediction:
        """Run anomaly inference on a dict of raw sensor readings.

        Args:
            asset_id: e.g. "maitri.gen1"
            readings: dict of {sensor_suffix: value}, e.g.
                      {"vibration_rms": 8.5, "oil_pressure_bar": 4.1, ...}

        Returns:
            AnomalyPrediction with score, risk_level, confidence.
        """
        if self._pipeline is None:
            raise RuntimeError("Model not loaded. Call load() or train() first.")

        vec = reading_to_feature_vector(readings)              # (N_FEATURES,)
        X   = vec.reshape(1, -1)                               # (1, N_FEATURES)
        score = float(self._pipeline.decision_function(X)[0])

        risk_level  = score_to_risk_level(score)
        confidence  = score_to_confidence(score)
        is_anomaly  = risk_level in ("WARNING", "CRITICAL")

        pred = AnomalyPrediction(
            asset_id=asset_id,
            sensor_readings=readings,
            anomaly_score=score,
            risk_level=risk_level,
            is_anomaly=is_anomaly,
            confidence=confidence,
            feature_vector=vec.tolist(),
        )

        if is_anomaly:
            log.warning(
                "vibration_model.anomaly_detected",
                asset_id=asset_id,
                risk_level=risk_level,
                score=round(score, 4),
                confidence=round(confidence, 3),
                readings={k: round(v, 2) for k, v in readings.items()},
            )

        return pred

    def predict_batch(
        self,
        asset_id: str,
        readings_list: List[Dict[str, float]],
    ) -> List[AnomalyPrediction]:
        """Run inference on a batch of readings (more efficient than one-by-one)."""
        if self._pipeline is None:
            raise RuntimeError("Model not loaded.")

        vecs = np.stack([reading_to_feature_vector(r) for r in readings_list])
        scores = self._pipeline.decision_function(vecs)

        return [
            AnomalyPrediction(
                asset_id=asset_id,
                sensor_readings=readings_list[i],
                anomaly_score=float(scores[i]),
                risk_level=score_to_risk_level(float(scores[i])),
                is_anomaly=score_to_risk_level(float(scores[i])) != "NOMINAL",
                confidence=score_to_confidence(float(scores[i])),
                feature_vector=vecs[i].tolist(),
            )
            for i in range(len(readings_list))
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata
