"""Cloud AI Engine package.

Provides scheduled ML-based forecasting for Antarctic station operations.

Implemented models:
  - Model 1: Prophet fuel burn rate forecaster
    Predicts daily diesel consumption for next 7/30/90 days with
    confidence intervals. Incorporates temperature, crew count, wind
    speed, and generator load as regressors. Runs per-station (Maitri
    and Bharati have separate trained models).
    File: cloud.ai_engine.fuel_model

Planned (not yet implemented):
  - Model 3: LSTM Autoencoder multi-sensor anomaly detector
    (cloud.ai_engine.autoencoder)
  - Model 5: Energy balance / microgrid forecast
    (cloud.ai_engine.energy_model)

Imports are lazy so the module can be imported without Prophet/pandas
being loaded until actually needed (Prophet takes ~2s to import).

Public API:
    from cloud.ai_engine import FuelForecastModel
    from cloud.ai_engine import FuelForecast
    from cloud.ai_engine import DayForecast
"""
from __future__ import annotations


def __getattr__(name: str):
    """Lazy import — avoids Prophet's slow startup at module import time."""
    if name == "FuelForecastModel":
        from cloud.ai_engine.fuel_model import FuelForecastModel
        return FuelForecastModel
    if name == "FuelForecast":
        from cloud.ai_engine.fuel_model import FuelForecast
        return FuelForecast
    if name == "DayForecast":
        from cloud.ai_engine.fuel_model import DayForecast
        return DayForecast
    if name == "ForecastSummary":
        from cloud.ai_engine.fuel_model import ForecastSummary
        return ForecastSummary
    raise AttributeError(f"module 'cloud.ai_engine' has no attribute {name!r}")


__all__ = [
    "FuelForecastModel",
    "FuelForecast",
    "DayForecast",
    "ForecastSummary",
]
