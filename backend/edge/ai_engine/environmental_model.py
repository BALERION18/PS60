"""
Environmental Monitoring Model for Antarctic conditions.

Uses gradient boosting (XGBoost) for weather pattern classification and 
ARIMA-style time series forecasting for temperature/wind predictions.
Provides environmental alerts and equipment stress predictions.

Features: temperature, humidity, pressure, wind speed/direction, visibility
Targets: weather_pattern, alert_level, equipment_stress, comfort_index
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import structlog
import warnings
from dataclasses import dataclass
import joblib

# ML imports
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    classification_report, accuracy_score, mean_absolute_error,
    mean_squared_error, r2_score
)
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

from edge.ai_engine.model_store import ModelStore, ModelMetadata, get_model_store, utcnow_iso

log = structlog.get_logger(__name__)

# Model configuration
MODEL_NAME = "environmental_monitoring"
MODEL_VERSION = "v1"

# Weather patterns
WEATHER_PATTERNS = [
    "CLEAR", "PARTLY_CLOUDY", "OVERCAST", 
    "LIGHT_SNOW", "HEAVY_SNOW", "BLIZZARD",
    "FOG", "STORM"
]

# Alert severity mapping
ALERT_SEVERITY = {
    "EXTREME_COLD_WARNING": 5,
    "SEVERE_COLD_WARNING": 4,
    "UNUSUAL_WARMTH_ALERT": 3,
    "EXTREME_WIND_WARNING": 5,
    "HIGH_WIND_WARNING": 4,
    "ZERO_VISIBILITY_WARNING": 5,
    "LOW_VISIBILITY_WARNING": 3,
    "BLIZZARD_WARNING": 5,
    "STORM_WARNING": 4,
}

# Feature engineering parameters
LOOKBACK_HOURS = 24  # Hours of history for time series features
FORECAST_HORIZON = 6  # Hours to forecast ahead

# Model hyperparameters
GBT_N_ESTIMATORS = 50
GBT_MAX_DEPTH = 4
GBT_LEARNING_RATE = 0.2

@dataclass
class EnvironmentalPrediction:
    """Output from environmental monitoring model."""
    timestamp: str
    current_conditions: Dict[str, float]
    forecasted_conditions: Dict[str, float]
    weather_pattern: str
    weather_confidence: float
    alert_level: int
    active_alerts: List[str]
    equipment_stress: float
    comfort_index: float
    forecast_horizon_hours: int
    risk_assessment: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "current_conditions": self.current_conditions,
            "forecasted_conditions": self.forecasted_conditions,
            "weather_pattern": self.weather_pattern,
            "weather_confidence": self.weather_confidence,
            "alert_level": self.alert_level,
            "active_alerts": self.active_alerts,
            "equipment_stress": self.equipment_stress,
            "comfort_index": self.comfort_index,
            "forecast_horizon_hours": self.forecast_horizon_hours,
            "risk_assessment": self.risk_assessment,
            "recommendations": self.recommendations,
        }

class EnvironmentalMonitoringModel:
    """Multi-target environmental monitoring model.
    
    Usage — training:
        model = EnvironmentalMonitoringModel()
        model.train(df_environmental)
        model.evaluate(df_val)
        model.save()
    
    Usage — inference:
        model = EnvironmentalMonitoringModel.load()
        pred = model.predict(current_conditions)
    """
    
    def __init__(self):
        # Weather pattern classifier
        self.weather_classifier: Optional[Pipeline] = None
        
        # Time series forecasters for key variables
        self.temperature_forecaster: Optional[Pipeline] = None
        self.wind_forecaster: Optional[Pipeline] = None
        self.humidity_forecaster: Optional[Pipeline] = None
        self.pressure_forecaster: Optional[Pipeline] = None
        
        # Regression models for derived metrics
        self.equipment_stress_model: Optional[Pipeline] = None
        self.comfort_index_model: Optional[Pipeline] = None
        
        # Label encoder for weather patterns
        self.weather_encoder: Optional[LabelEncoder] = None
        
        # Feature names and metadata
        self.feature_names: List[str] = []
        self.weather_patterns: List[str] = WEATHER_PATTERNS
        
        # Model persistence
        self._metadata: Optional[ModelMetadata] = None
        self._store: ModelStore = get_model_store()
    
    def _engineer_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Engineer features for environmental prediction."""
        features = []
        feature_names = []
        
        # Current conditions
        current_features = [
            'air_temperature', 'ground_temperature', 'equipment_temperature',
            'wind_speed', 'wind_direction', 'humidity', 'pressure', 'visibility',
            'snow_accumulation'
        ]
        
        for feat in current_features:
            if feat in df.columns:
                features.append(df[feat].values)
                feature_names.append(feat)
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['month'] = df['timestamp'].dt.month
        
        # Cyclical encoding for time features
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
        
        time_features = ['hour_sin', 'hour_cos', 'day_sin', 'day_cos']
        for feat in time_features:
            features.append(df[feat].values)
            feature_names.append(feat)
        
        # Derived features
        if 'air_temperature' in df.columns and 'wind_speed' in df.columns:
            # Wind chill calculation
            df['wind_chill'] = 13.12 + 0.6215 * df['air_temperature'] - 11.37 * (df['wind_speed'] ** 0.16) + 0.3965 * df['air_temperature'] * (df['wind_speed'] ** 0.16)
            features.append(df['wind_chill'].values)
            feature_names.append('wind_chill')
        
        if 'air_temperature' in df.columns and 'humidity' in df.columns:
            # Heat index (adapted for cold conditions)
            df['heat_index'] = df['air_temperature'] + 0.5 * (df['humidity'] - 50) / 10
            features.append(df['heat_index'].values)
            feature_names.append('heat_index')
        
        # Stability indicators
        if len(features) > 0:
            # Rolling statistics for trend detection
            for window in [6, 12, 24]:  # 6h, 12h, 24h windows
                for feat_idx, feat_name in enumerate(feature_names[:len(current_features)]):
                    if feat_name in current_features:
                        values = features[feat_idx]
                        df[f'{feat_name}_trend_{window}h'] = pd.Series(values).rolling(window, min_periods=1).mean().diff()
                        df[f'{feat_name}_std_{window}h'] = pd.Series(values).rolling(window, min_periods=1).std().fillna(0)
                        
                        features.append(df[f'{feat_name}_trend_{window}h'].fillna(0).values)
                        feature_names.append(f'{feat_name}_trend_{window}h')
                        features.append(df[f'{feat_name}_std_{window}h'].values)
                        feature_names.append(f'{feat_name}_std_{window}h')
        
        # Stack all features
        X = np.column_stack(features)
        
        # Handle any NaN values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        self.feature_names = feature_names
        
        return X, {'feature_names': feature_names}
    
    def _prepare_targets(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Prepare target variables."""
        targets = {}
        
        # Weather pattern classification target
        if 'weather_pattern' in df.columns:
            self.weather_encoder = LabelEncoder()
            targets['weather_pattern'] = self.weather_encoder.fit_transform(df['weather_pattern'])
            self.weather_patterns = self.weather_encoder.classes_.tolist()
        
        # Regression targets
        regression_targets = ['equipment_stress', 'comfort_index']
        for target in regression_targets:
            if target in df.columns:
                targets[target] = df[target].values
        
        # Alert level target (derived from alert count and severity)
        if 'alerts' in df.columns:
            alert_levels = []
            for alerts in df['alerts']:
                level = 0
                for alert in alerts:
                    level += ALERT_SEVERITY.get(alert, 1)
                alert_levels.append(min(5, level))  # Cap at level 5
            targets['alert_level'] = np.array(alert_levels)
        
        # Future values for forecasting (shifted targets)
        forecast_targets = ['air_temperature', 'wind_speed', 'humidity', 'pressure']
        for target in forecast_targets:
            if target in df.columns:
                future_values = df[target].shift(-FORECAST_HORIZON).ffill()
                targets[f'{target}_future'] = future_values.values
        
        return targets
    
    def train(self, df_environmental: pd.DataFrame) -> None:
        """Train all sub-models on environmental data."""
        log.info(
            "environmental_model.training_start",
            n_samples=len(df_environmental),
            n_features=len(df_environmental.columns),
        )
        
        # Engineer features
        X, feature_info = self._engineer_features(df_environmental)
        targets = self._prepare_targets(df_environmental)
        
        log.info(
            "environmental_model.features_engineered",
            n_features=X.shape[1],
            feature_names=feature_info['feature_names'][:10],  # First 10 for brevity
        )
        
        # Train weather pattern classifier
        if 'weather_pattern' in targets:
            log.info("environmental_model.training_weather_classifier")
            self.weather_classifier = Pipeline([
                ('scaler', StandardScaler()),
                ('gbt', GradientBoostingClassifier(
                    n_estimators=GBT_N_ESTIMATORS,
                    max_depth=GBT_MAX_DEPTH,
                    learning_rate=GBT_LEARNING_RATE,
                    random_state=42,
                ))
            ])
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.weather_classifier.fit(X, targets['weather_pattern'])
        
        # Train regression models
        regression_models = {
            'equipment_stress': 'equipment_stress_model',
            'comfort_index': 'comfort_index_model',
        }
        
        for target_name, model_attr in regression_models.items():
            if target_name in targets:
                log.info(f"environmental_model.training_{target_name}_model")
                
                model = Pipeline([
                    ('scaler', StandardScaler()),
                    ('gbt', GradientBoostingRegressor(
                        n_estimators=GBT_N_ESTIMATORS,
                        max_depth=GBT_MAX_DEPTH,
                        learning_rate=GBT_LEARNING_RATE,
                        random_state=42,
                    ))
                ])
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X, targets[target_name])
                
                setattr(self, model_attr, model)
        
        # Train forecasting models
        forecast_models = {
            'air_temperature_future': 'temperature_forecaster',
            'wind_speed_future': 'wind_forecaster',
            'humidity_future': 'humidity_forecaster',
            'pressure_future': 'pressure_forecaster',
        }
        
        for target_name, model_attr in forecast_models.items():
            if target_name in targets:
                log.info(f"environmental_model.training_{model_attr}")
                
                model = Pipeline([
                    ('scaler', StandardScaler()),
                    ('gbt', GradientBoostingRegressor(
                        n_estimators=GBT_N_ESTIMATORS,
                        max_depth=GBT_MAX_DEPTH,
                        learning_rate=GBT_LEARNING_RATE,
                        random_state=42,
                    ))
                ])
                
                # Remove samples with NaN targets (end of dataset)
                valid_mask = ~np.isnan(targets[target_name])
                X_valid = X[valid_mask]
                y_valid = targets[target_name][valid_mask]
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X_valid, y_valid)
                
                setattr(self, model_attr, model)
        
        log.info("environmental_model.training_done")
    
    def predict(
        self,
        current_conditions: Dict[str, float],
        historical_data: Optional[pd.DataFrame] = None,
    ) -> EnvironmentalPrediction:
        """Predict environmental conditions and alerts."""
        # Create a minimal DataFrame for feature engineering
        timestamp = datetime.now(timezone.utc)
        
        # If historical data not provided, create synthetic recent history
        if historical_data is None:
            historical_data = pd.DataFrame([current_conditions] * (LOOKBACK_HOURS + 1))
            historical_data['timestamp'] = [
                timestamp - timedelta(hours=i) for i in range(LOOKBACK_HOURS, -1, -1)
            ]
            # Add some synthetic weather pattern for consistency
            historical_data['weather_pattern'] = 'CLEAR'
            historical_data['alerts'] = [[] for _ in range(len(historical_data))]
            historical_data['equipment_stress'] = 0.3
            historical_data['comfort_index'] = 50.0
        
        # Engineer features
        X, _ = self._engineer_features(historical_data)
        current_X = X[-1:]  # Use last row (current conditions)
        
        # Weather pattern prediction
        weather_pattern = "UNKNOWN"
        weather_confidence = 0.0
        if self.weather_classifier is not None and self.weather_encoder is not None:
            weather_probs = self.weather_classifier.predict_proba(current_X)[0]
            weather_idx = np.argmax(weather_probs)
            # Handle unseen labels gracefully
            if weather_idx < len(self.weather_encoder.classes_):
                weather_pattern = self.weather_encoder.inverse_transform([weather_idx])[0]
                weather_confidence = float(weather_probs[weather_idx])
            else:
                weather_pattern = "UNKNOWN"
                weather_confidence = 0.5
        
        # Equipment stress prediction
        equipment_stress = 0.3  # Default
        if self.equipment_stress_model is not None:
            equipment_stress = float(self.equipment_stress_model.predict(current_X)[0])
        
        # Comfort index prediction
        comfort_index = 50.0  # Default
        if self.comfort_index_model is not None:
            comfort_index = float(self.comfort_index_model.predict(current_X)[0])
        
        # Forecast future conditions
        forecasted_conditions = {}
        forecast_models = [
            ('air_temperature', 'temperature_forecaster'),
            ('wind_speed', 'wind_forecaster'),
            ('humidity', 'humidity_forecaster'),
            ('pressure', 'pressure_forecaster'),
        ]
        
        for condition, model_attr in forecast_models:
            model = getattr(self, model_attr, None)
            if model is not None:
                forecast_val = float(model.predict(current_X)[0])
                forecasted_conditions[condition] = forecast_val
            else:
                # Use current value as forecast if no model
                forecasted_conditions[condition] = current_conditions.get(condition, 0.0)
        
        # Generate alerts based on conditions
        active_alerts = []
        alert_level = 0
        
        temp = current_conditions.get('air_temperature', 0.0)
        wind = current_conditions.get('wind_speed', 0.0)
        visibility = current_conditions.get('visibility', 10000.0)
        
        # Temperature alerts
        if temp < -40.0:
            active_alerts.append("EXTREME_COLD_WARNING")
            alert_level += 5
        elif temp < -30.0:
            active_alerts.append("SEVERE_COLD_WARNING")
            alert_level += 4
        elif temp > 5.0:
            active_alerts.append("UNUSUAL_WARMTH_ALERT")
            alert_level += 3
        
        # Wind alerts
        if wind > 50.0:
            active_alerts.append("EXTREME_WIND_WARNING")
            alert_level += 5
        elif wind > 30.0:
            active_alerts.append("HIGH_WIND_WARNING")
            alert_level += 4
        
        # Visibility alerts
        if visibility < 100:
            active_alerts.append("ZERO_VISIBILITY_WARNING")
            alert_level += 5
        elif visibility < 500:
            active_alerts.append("LOW_VISIBILITY_WARNING")
            alert_level += 3
        
        # Pattern-specific alerts
        if weather_pattern == "BLIZZARD":
            active_alerts.append("BLIZZARD_WARNING")
            alert_level += 5
        elif weather_pattern == "STORM":
            active_alerts.append("STORM_WARNING")
            alert_level += 4
        
        alert_level = min(5, alert_level)
        
        # Risk assessment
        if alert_level >= 4:
            risk_assessment = "HIGH"
        elif alert_level >= 2:
            risk_assessment = "MEDIUM"
        else:
            risk_assessment = "LOW"
        
        # Generate recommendations
        recommendations = []
        
        if equipment_stress > 0.7:
            recommendations.append("Monitor equipment closely - high stress conditions")
        if comfort_index < 30:
            recommendations.append("Minimize outdoor activities - poor conditions")
        if weather_pattern in ["BLIZZARD", "STORM"]:
            recommendations.append("Shelter in place - extreme weather")
        if temp < -35.0:
            recommendations.append("Check heating systems - extreme cold")
        if wind > 35.0:
            recommendations.append("Secure loose equipment - high winds")
        if not recommendations:
            recommendations.append("Normal operations - monitor conditions")
        
        return EnvironmentalPrediction(
            timestamp=timestamp.isoformat(),
            current_conditions=current_conditions,
            forecasted_conditions=forecasted_conditions,
            weather_pattern=weather_pattern,
            weather_confidence=weather_confidence,
            alert_level=alert_level,
            active_alerts=active_alerts,
            equipment_stress=equipment_stress,
            comfort_index=comfort_index,
            forecast_horizon_hours=FORECAST_HORIZON,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
        )
    
    def evaluate(self, df_val: pd.DataFrame) -> Dict[str, float]:
        """Evaluate model performance on validation data."""
        log.info("environmental_model.evaluation_start", n_samples=len(df_val))
        
        X, _ = self._engineer_features(df_val)
        targets = self._prepare_targets(df_val)
        
        metrics = {}
        
        # Weather pattern classification metrics
        if self.weather_classifier is not None and 'weather_pattern' in targets:
            y_pred = self.weather_classifier.predict(X)
            y_true = targets['weather_pattern']
            
            accuracy = accuracy_score(y_true, y_pred)
            metrics['weather_pattern_accuracy'] = accuracy
            
            log.info(f"environmental_model.weather_accuracy", accuracy=round(accuracy, 4))
        
        # Regression metrics
        regression_models = [
            ('equipment_stress', self.equipment_stress_model),
            ('comfort_index', self.comfort_index_model),
        ]
        
        for target_name, model in regression_models:
            if model is not None and target_name in targets:
                y_pred = model.predict(X)
                y_true = targets[target_name]
                
                mae = mean_absolute_error(y_true, y_pred)
                rmse = np.sqrt(mean_squared_error(y_true, y_pred))
                r2 = r2_score(y_true, y_pred)
                
                metrics[f'{target_name}_mae'] = mae
                metrics[f'{target_name}_rmse'] = rmse
                metrics[f'{target_name}_r2'] = r2
                
                log.info(
                    f"environmental_model.{target_name}_metrics",
                    mae=round(mae, 4),
                    rmse=round(rmse, 4),
                    r2=round(r2, 4),
                )
        
        # Forecasting metrics
        forecast_models = [
            ('air_temperature_future', self.temperature_forecaster),
            ('wind_speed_future', self.wind_forecaster),
            ('humidity_future', self.humidity_forecaster),
            ('pressure_future', self.pressure_forecaster),
        ]
        
        for target_name, model in forecast_models:
            if model is not None and target_name in targets:
                # Remove NaN targets for evaluation
                valid_mask = ~np.isnan(targets[target_name])
                X_valid = X[valid_mask]
                y_true_valid = targets[target_name][valid_mask]
                
                if len(y_true_valid) > 0:
                    y_pred = model.predict(X_valid)
                    
                    mae = mean_absolute_error(y_true_valid, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_true_valid, y_pred))
                    
                    metrics[f'{target_name}_mae'] = mae
                    metrics[f'{target_name}_rmse'] = rmse
                    
                    log.info(
                        f"environmental_model.{target_name}_forecast_metrics",
                        mae=round(mae, 4),
                        rmse=round(rmse, 4),
                    )
        
        log.info("environmental_model.evaluation_done")
        return metrics
    
    def save(
        self,
        val_scores: Optional[Dict[str, float]] = None,
        n_training_samples: int = 0,
        notes: str = "",
    ) -> None:
        """Save model to disk."""
        models_dict = {}
        
        # Save all trained models
        if self.weather_classifier is not None:
            models_dict['weather_classifier'] = self.weather_classifier
        if self.temperature_forecaster is not None:
            models_dict['temperature_forecaster'] = self.temperature_forecaster
        if self.wind_forecaster is not None:
            models_dict['wind_forecaster'] = self.wind_forecaster
        if self.humidity_forecaster is not None:
            models_dict['humidity_forecaster'] = self.humidity_forecaster
        if self.pressure_forecaster is not None:
            models_dict['pressure_forecaster'] = self.pressure_forecaster
        if self.equipment_stress_model is not None:
            models_dict['equipment_stress_model'] = self.equipment_stress_model
        if self.comfort_index_model is not None:
            models_dict['comfort_index_model'] = self.comfort_index_model
        
        payload = {
            'models': models_dict,
            'weather_encoder': self.weather_encoder,
            'feature_names': self.feature_names,
            'weather_patterns': self.weather_patterns,
        }
        
        metadata = ModelMetadata(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            trained_at=utcnow_iso(),
            algorithm="Gradient Boosting (Multi-target)",
            feature_names=self.feature_names,
            n_features=len(self.feature_names),
            val_scores=val_scores or {},
            hyperparameters={
                "n_estimators": GBT_N_ESTIMATORS,
                "max_depth": GBT_MAX_DEPTH,
                "learning_rate": GBT_LEARNING_RATE,
                "lookback_hours": LOOKBACK_HOURS,
                "forecast_horizon": FORECAST_HORIZON,
            },
            n_training_samples=n_training_samples,
            notes=notes,
        )
        
        self._store.save(payload, metadata)
        self._metadata = metadata
        
        log.info(
            "environmental_model.saved",
            model_name=MODEL_NAME,
            version=MODEL_VERSION,
            n_submodels=len(models_dict),
        )
    
    @classmethod
    def load(cls, version: str = MODEL_VERSION) -> "EnvironmentalMonitoringModel":
        """Load model from disk."""
        store = get_model_store()
        payload, metadata = store.load(MODEL_NAME, version)
        
        model = cls()
        models_dict = payload['models']
        
        # Load all sub-models
        model.weather_classifier = models_dict.get('weather_classifier')
        model.temperature_forecaster = models_dict.get('temperature_forecaster')
        model.wind_forecaster = models_dict.get('wind_forecaster')
        model.humidity_forecaster = models_dict.get('humidity_forecaster')
        model.pressure_forecaster = models_dict.get('pressure_forecaster')
        model.equipment_stress_model = models_dict.get('equipment_stress_model')
        model.comfort_index_model = models_dict.get('comfort_index_model')
        
        model.weather_encoder = payload['weather_encoder']
        model.feature_names = payload['feature_names']
        model.weather_patterns = payload['weather_patterns']
        model._metadata = metadata
        
        log.info(
            "environmental_model.loaded",
            model_name=MODEL_NAME,
            version=version,
            trained_at=metadata.trained_at,
        )
        
        return model
    
    @classmethod
    def load_or_none(cls, version: str = MODEL_VERSION) -> Optional["EnvironmentalMonitoringModel"]:
        """Load model or return None if not found."""
        try:
            return cls.load(version)
        except Exception as e:
            log.warning("environmental_model.load_failed", error=str(e))
            return None
    
    @property
    def is_loaded(self) -> bool:
        return self._metadata is not None
    
    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata