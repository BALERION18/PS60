"""Edge AI Engine package.

Provides real-time ML-based anomaly detection and predictive maintenance
for Antarctic station generator and infrastructure sensors.

Implemented models:
  - Model 2: Isolation Forest vibration anomaly detector
    Detects bearing wear, oil pressure drops, coolant overtemp,
    power surges, and fuel line restrictions from 5 sensor streams.
    File: edge.ai_engine.vibration_model

  - Model 4: Random Forest predictive maintenance classifier
    Classifies maintenance urgency (NONE/LOW/MEDIUM/HIGH) from 15
    asset-health features including runtime hours, IF anomaly scores,
    and rolling 7-day sensor trends.
    File: edge.ai_engine.maintenance_model

Imports are lazy so ML-only code (feature_builder, vibration_model,
maintenance_model) can be imported without the full FastAPI/SQLAlchemy
stack being present.  The full AIEngineService (which needs Redis +
SQLAlchemy) is only imported when explicitly requested.

Public API (for edge/main.py):
    from edge.ai_engine import AIEngineService

Public API (for training/testing — no DB required):
    from edge.ai_engine.vibration_model import VibrationAnomalyModel
    from edge.ai_engine.maintenance_model import MaintenanceModel
    from edge.ai_engine.feature_builder import reading_to_feature_vector
    from edge.ai_engine.maintenance_features import build_feature_vector

Planned (not yet implemented):
  - Model 1: LSTM fuel burn rate forecaster     (edge.ai_engine.fuel_model)
  - Model 3: LSTM Autoencoder multi-sensor      (edge.ai_engine.autoencoder)
  - Model 5: Energy balance forecast            (edge.ai_engine.energy_model)
"""
from __future__ import annotations


def __getattr__(name: str):
    """Lazy import — avoids dragging in SQLAlchemy/Redis at import time."""
    if name == "AIEngineService":
        from edge.ai_engine.service import AIEngineService
        return AIEngineService
    if name == "VibrationAnomalyModel":
        from edge.ai_engine.vibration_model import VibrationAnomalyModel
        return VibrationAnomalyModel
    if name == "AnomalyPrediction":
        from edge.ai_engine.vibration_model import AnomalyPrediction
        return AnomalyPrediction
    if name == "MaintenanceModel":
        from edge.ai_engine.maintenance_model import MaintenanceModel
        return MaintenanceModel
    if name == "MaintenancePrediction":
        from edge.ai_engine.maintenance_model import MaintenancePrediction
        return MaintenancePrediction
    raise AttributeError(f"module 'edge.ai_engine' has no attribute {name!r}")


__all__ = [
    "AIEngineService",
    "VibrationAnomalyModel",
    "AnomalyPrediction",
    "MaintenanceModel",
    "MaintenancePrediction",
]
