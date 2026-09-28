"""Prophet-based fuel burn rate forecaster — Model 1.

Why Prophet instead of LSTM:
  - Antarctic fuel consumption has strong, well-defined seasonality
    (winter peak May–Aug, summer trough Nov–Feb). Prophet explicitly
    models Fourier-series seasonality — perfect for this.
  - We have limited labeled data (a few years of expedition records).
    Prophet works well with 1–3 years; LSTM needs 5+ years to converge.
  - Prophet produces calibrated uncertainty intervals out of the box.
    For fuel planning, knowing "30-day forecast ± 15%" is more useful
    than a point estimate.
  - Prophet is interpretable: you can plot trend, weekly, and yearly
    components and show operators exactly what is driving the forecast.
  - scikit-learn already in deps; Prophet adds minimal overhead.

Model configuration:
  - Yearly seasonality:  Fourier order 8 (captures sharp winter peak)
  - Weekly seasonality:  Fourier order 3 (weekend/weekday patterns)
  - Changepoint prior:   0.15 (allows moderate trend flexibility)
  - Seasonality prior:   12.0 (strong seasonal signal)
  - Regressors:          ambient_temp_c, crew_count, is_winter,
                         wind_speed_ms, generator_load_kw

Output — FuelForecast dataclass:
    station_id          — which station
    generated_at        — UTC timestamp of forecast run
    horizon_days        — number of days forecast
    daily_forecast      — list of DayForecast (date, predicted_burn,
                          lower, upper, tank_level_litres)
    summary             — aggregated 7/30/90 day totals
    days_to_minimum     — days until tank hits safety threshold (25%)
    risk_level          — NOMINAL / WARNING / CRITICAL
    model_mae_litres    — training MAE from last evaluation

Scheduled run:
    The cloud backend runs this model once per day via APScheduler
    (configured in cloud/main.py — not yet wired, that's a separate task).
    Results are written to the ai_predictions table.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

from cloud.ai_engine.fuel_features import (
    REGRESSOR_COLS,
    STATION_CONSTANTS,
    build_future_df,
    burn_to_tank_level,
    compute_burn_metrics,
    compute_coverage,
    days_until_threshold,
)
from edge.ai_engine.model_store import (
    ModelMetadata,
    ModelStore,
    get_model_store,
    utcnow_iso,
)

log = structlog.get_logger(__name__)

MODEL_NAME    = "fuel_burn_prophet"
MODEL_VERSION = "v1"

# Risk thresholds based on tank percentage
THRESHOLD_WARNING_PCT  = 0.35   # 35% tank -> WARNING
THRESHOLD_CRITICAL_PCT = 0.20   # 20% tank -> CRITICAL


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DayForecast:
    """Single-day fuel burn prediction."""
    date: str               # ISO date string
    predicted_burn_litres: float
    lower_bound_litres: float
    upper_bound_litres: float
    tank_level_litres: float
    tank_pct: float

    def to_dict(self) -> dict:
        return {
            "date":                   self.date,
            "predicted_burn_litres":  round(self.predicted_burn_litres, 1),
            "lower_bound_litres":     round(self.lower_bound_litres, 1),
            "upper_bound_litres":     round(self.upper_bound_litres, 1),
            "tank_level_litres":      round(self.tank_level_litres, 1),
            "tank_pct":               round(self.tank_pct, 3),
        }


@dataclass
class ForecastSummary:
    """Aggregated totals for 7, 30, 90 day windows."""
    total_7d_litres: float
    total_30d_litres: float
    total_90d_litres: float
    avg_daily_7d: float
    avg_daily_30d: float
    peak_day_litres: float
    peak_day_date: str

    def to_dict(self) -> dict:
        return {
            "total_7d_litres":   round(self.total_7d_litres, 1),
            "total_30d_litres":  round(self.total_30d_litres, 1),
            "total_90d_litres":  round(self.total_90d_litres, 1),
            "avg_daily_7d":      round(self.avg_daily_7d, 1),
            "avg_daily_30d":     round(self.avg_daily_30d, 1),
            "peak_day_litres":   round(self.peak_day_litres, 1),
            "peak_day_date":     self.peak_day_date,
        }


@dataclass
class FuelForecast:
    """Complete output of one model run."""
    station_id: str
    generated_at: str
    horizon_days: int
    current_tank_litres: float
    tank_capacity_litres: float
    daily_forecast: List[DayForecast]
    summary: ForecastSummary
    days_to_warning: Optional[int]    # days until tank hits WARNING threshold
    days_to_critical: Optional[int]   # days until tank hits CRITICAL threshold
    risk_level: str                   # NOMINAL | WARNING | CRITICAL
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION
    model_mae_litres: float = 0.0

    def to_dict(self) -> dict:
        return {
            "station_id":           self.station_id,
            "generated_at":         self.generated_at,
            "horizon_days":         self.horizon_days,
            "current_tank_litres":  round(self.current_tank_litres, 1),
            "tank_capacity_litres": self.tank_capacity_litres,
            "risk_level":           self.risk_level,
            "days_to_warning":      self.days_to_warning,
            "days_to_critical":     self.days_to_critical,
            "summary":              self.summary.to_dict(),
            "daily_forecast":       [d.to_dict() for d in self.daily_forecast],
            "model_name":           self.model_name,
            "model_version":        self.model_version,
            "model_mae_litres":     round(self.model_mae_litres, 1),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Main model class
# ---------------------------------------------------------------------------

class FuelForecastModel:
    """Prophet fuel burn rate forecaster.

    Usage — training:
        model = FuelForecastModel("maitri")
        model.train(df_train)
        model.evaluate(df_val)
        model.save()

    Usage — inference:
        model = FuelForecastModel.load("maitri")
        forecast = model.forecast(
            current_tank_litres=95000,
            horizon_days=90,
        )
        print(forecast.risk_level)
        print(forecast.days_to_critical)
    """

    def __init__(self, station_id: str = "maitri") -> None:
        self._station_id = station_id
        self._model = None                          # Prophet instance
        self._metadata: Optional[ModelMetadata] = None
        self._store: ModelStore = get_model_store()
        self._last_train_date: Optional[pd.Timestamp] = None
        self._val_mae: float = 0.0

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, df_train: pd.DataFrame) -> None:
        """Fit the Prophet model on a daily fuel consumption DataFrame.

        Args:
            df_train: Prophet-format DataFrame with ds, y, and regressor cols.
                      NaN rows are automatically dropped before fitting.
        """
        from prophet import Prophet  # lazy import — Prophet startup is slow

        df = df_train.dropna(subset=["y"]).copy()

        log.info(
            "fuel_model.training_start",
            station_id=self._station_id,
            n_days=len(df),
            date_range="%s to %s" % (df["ds"].min().date(), df["ds"].max().date()),
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            self._model = Prophet(
                yearly_seasonality   = False,   # we add manually with higher order
                weekly_seasonality   = True,
                daily_seasonality    = False,
                changepoint_prior_scale    = 0.15,
                seasonality_prior_scale    = 12.0,
                interval_width             = 0.90,  # 90% prediction interval
                uncertainty_samples        = 500,
            )

            # High-order yearly seasonality to capture sharp Antarctic winter peak
            self._model.add_seasonality(
                name="yearly",
                period=365.25,
                fourier_order=8,
            )

            # Add all regressors
            for col in REGRESSOR_COLS:
                if col in df.columns:
                    self._model.add_regressor(col, standardize=True)

            self._model.fit(df)

        self._last_train_date = df["ds"].max()

        log.info(
            "fuel_model.training_done",
            station_id=self._station_id,
            last_date=str(self._last_train_date.date()),
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, df_val: pd.DataFrame) -> Dict[str, float]:
        """Evaluate on a held-out validation set.

        Uses Prophet's in-sample prediction on the validation dates.
        Prints MAE, RMSE, MAPE, and interval coverage.
        """
        if self._model is None:
            raise RuntimeError("Model not trained.")

        df_val = df_val.dropna(subset=["y"]).copy()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self._model.predict(df_val[["ds"] + REGRESSOR_COLS])

        y_true     = df_val["y"].values
        y_pred     = forecast["yhat"].values
        y_lower    = forecast["yhat_lower"].values
        y_upper    = forecast["yhat_upper"].values

        metrics    = compute_burn_metrics(y_true, y_pred)
        coverage   = compute_coverage(y_true, y_lower, y_upper)

        metrics["coverage_90pct"] = coverage
        metrics["n_val_days"]     = len(df_val)

        self._val_mae = metrics["mae_litres"]

        print("\n" + "="*60)
        print("  FUEL BURN PROPHET MODEL — EVALUATION REPORT")
        print("  Station: %s" % self._station_id.upper())
        print("="*60)
        print("  Validation period : %s to %s" % (
            df_val["ds"].min().date(), df_val["ds"].max().date()))
        print("  Validation days   : %d" % len(df_val))
        print("  MAE               : %.1f L/day" % metrics["mae_litres"])
        print("  RMSE              : %.1f L/day" % metrics["rmse_litres"])
        print("  MAPE              : %.2f%%" % metrics["mape_pct"])
        print("  90%% PI Coverage  : %.1f%%" % coverage)

        # Monthly breakdown
        df_eval = df_val.copy()
        df_eval["yhat"]  = y_pred
        df_eval["month"] = pd.to_datetime(df_eval["ds"]).dt.month
        monthly_mae = df_eval.groupby("month").apply(
            lambda g: np.mean(np.abs(g["y"].values - g["yhat"].values))
        )
        print("\n  Monthly MAE (L/day):")
        months_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        for m in range(1, 13):
            if m in monthly_mae.index:
                print("    %-4s  %.1f" % (months_abbr[m-1], monthly_mae[m]))
        print("="*60 + "\n")

        log.info("fuel_model.evaluation", station_id=self._station_id, **metrics)
        return metrics

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------

    def forecast(
        self,
        current_tank_litres: float,
        horizon_days: int = 90,
        ambient_temp_forecast: Optional[np.ndarray] = None,
        crew_schedule: Optional[np.ndarray] = None,
        wind_forecast: Optional[np.ndarray] = None,
    ) -> FuelForecast:
        """Run a forward forecast from today.

        Args:
            current_tank_litres:    Current fuel level in litres.
            horizon_days:           Days to forecast (default 90).
            ambient_temp_forecast:  Optional external weather forecast.
            crew_schedule:          Optional planned crew counts.
            wind_forecast:          Optional wind speed forecast.

        Returns:
            FuelForecast with daily predictions and risk assessment.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call train() or load() first.")

        last_date = self._last_train_date or pd.Timestamp.now(tz="UTC")

        future_df = build_future_df(
            last_date             = last_date,
            horizon_days          = horizon_days,
            station_id            = self._station_id,
            ambient_temp_forecast = ambient_temp_forecast,
            crew_schedule         = crew_schedule,
            wind_forecast         = wind_forecast,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = self._model.predict(future_df)

        # Clip negatives — burn can't be negative
        predicted = np.maximum(raw["yhat"].values, 100.0)
        lower     = np.maximum(raw["yhat_lower"].values, 50.0)
        upper     = np.maximum(raw["yhat_upper"].values, 150.0)

        # Tank level depletion
        tank_levels = burn_to_tank_level(current_tank_litres, predicted)
        consts      = STATION_CONSTANTS.get(self._station_id, STATION_CONSTANTS["maitri"])
        capacity    = consts["tank_capacity_litres"]

        # Risk thresholds in litres
        warn_thresh = capacity * THRESHOLD_WARNING_PCT
        crit_thresh = capacity * THRESHOLD_CRITICAL_PCT

        days_to_warn = days_until_threshold(current_tank_litres, predicted, warn_thresh)
        days_to_crit = days_until_threshold(current_tank_litres, predicted, crit_thresh)

        # Overall risk level
        if days_to_crit is not None and days_to_crit <= 30:
            risk = "CRITICAL"
        elif days_to_warn is not None and days_to_warn <= 60:
            risk = "WARNING"
        else:
            risk = "NOMINAL"

        # Build daily forecasts
        dates = future_df["ds"].dt.strftime("%Y-%m-%d").tolist()
        daily = [
            DayForecast(
                date                  = dates[i],
                predicted_burn_litres = float(predicted[i]),
                lower_bound_litres    = float(lower[i]),
                upper_bound_litres    = float(upper[i]),
                tank_level_litres     = float(tank_levels[i]),
                tank_pct              = float(tank_levels[i] / capacity),
            )
            for i in range(horizon_days)
        ]

        # Summary stats
        summary = ForecastSummary(
            total_7d_litres  = float(predicted[:7].sum()),
            total_30d_litres = float(predicted[:30].sum()),
            total_90d_litres = float(predicted[:90].sum()),
            avg_daily_7d     = float(predicted[:7].mean()),
            avg_daily_30d    = float(predicted[:30].mean()),
            peak_day_litres  = float(predicted.max()),
            peak_day_date    = dates[int(predicted.argmax())],
        )

        fc = FuelForecast(
            station_id           = self._station_id,
            generated_at         = utcnow_iso(),
            horizon_days         = horizon_days,
            current_tank_litres  = current_tank_litres,
            tank_capacity_litres = capacity,
            daily_forecast       = daily,
            summary              = summary,
            days_to_warning      = days_to_warn,
            days_to_critical     = days_to_crit,
            risk_level           = risk,
            model_mae_litres     = self._val_mae,
        )

        log.info(
            "fuel_model.forecast_complete",
            station_id    = self._station_id,
            horizon_days  = horizon_days,
            risk_level    = risk,
            avg_daily_30d = round(summary.avg_daily_30d, 1),
            days_to_warn  = days_to_warn,
            days_to_crit  = days_to_crit,
        )
        return fc

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(
        self,
        val_scores: Optional[Dict[str, float]] = None,
        n_training_samples: int = 0,
        notes: str = "",
    ) -> None:
        """Persist the trained model and metadata."""
        if self._model is None:
            raise RuntimeError("Nothing to save — train() first.")

        # Use station-specific model name so Maitri and Bharati models
        # don't overwrite each other
        model_name = f"{MODEL_NAME}_{self._station_id}"

        metadata = ModelMetadata(
            model_name        = model_name,
            model_version     = MODEL_VERSION,
            trained_at        = utcnow_iso(),
            algorithm         = "Prophet",
            feature_names     = REGRESSOR_COLS,
            n_features        = len(REGRESSOR_COLS),
            n_training_samples= n_training_samples,
            hyperparameters   = {
                "changepoint_prior_scale": 0.15,
                "seasonality_prior_scale": 12.0,
                "yearly_fourier_order":    8,
                "interval_width":          0.90,
                "regressors":              REGRESSOR_COLS,
                "station_id":              self._station_id,
                "threshold_warning_pct":   THRESHOLD_WARNING_PCT,
                "threshold_critical_pct":  THRESHOLD_CRITICAL_PCT,
            },
            val_scores = val_scores or {},
            notes      = notes,
        )
        self._metadata = metadata
        self._store.save(self._model, metadata)

    @classmethod
    def load(
        cls,
        station_id: str = "maitri",
        version: str    = MODEL_VERSION,
        store: Optional[ModelStore] = None,
    ) -> "FuelForecastModel":
        """Load a trained model from disk."""
        _store     = store or get_model_store()
        model_name = f"{MODEL_NAME}_{station_id}"
        instance   = cls(station_id=station_id)
        instance._store = _store
        instance._model, instance._metadata = _store.load(model_name, version)

        # Restore last training date from metadata notes
        if instance._metadata and instance._metadata.val_scores:
            instance._val_mae = instance._metadata.val_scores.get("mae_litres", 0.0)

        log.info(
            "fuel_model.loaded",
            station_id = station_id,
            version    = version,
            trained_at = instance._metadata.trained_at if instance._metadata else "unknown",
        )
        return instance

    @classmethod
    def load_or_none(
        cls,
        station_id: str = "maitri",
        version: str    = MODEL_VERSION,
    ) -> Optional["FuelForecastModel"]:
        """Like load() but returns None instead of raising if not found."""
        try:
            return cls.load(station_id=station_id, version=version)
        except FileNotFoundError:
            log.warning(
                "fuel_model.not_found",
                station_id = station_id,
                version    = version,
                hint       = "Run: python -m scripts.train_fuel_model",
            )
            return None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def station_id(self) -> str:
        return self._station_id

    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata
