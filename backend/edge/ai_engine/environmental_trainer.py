"""
Training script for environmental monitoring model.

Usage:
    python -m edge.ai_engine.environmental_trainer --data-days 365 --seed 42
"""

import argparse
import logging
import structlog
from typing import Optional
import pandas as pd

from edge.ai_engine.environmental_synthetic_data import generate_train_val_split, describe_environmental_data
from edge.ai_engine.environmental_model import EnvironmentalMonitoringModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = structlog.get_logger(__name__)

def run_environmental_training(
    data_days: int = 365,
    validation_split: float = 0.2,
    seed: Optional[int] = None,
    notes: str = "",
) -> EnvironmentalMonitoringModel:
    """Run the full environmental monitoring model training pipeline."""
    
    log.info(
        "environmental_trainer.starting",
        data_days=data_days,
        validation_split=validation_split,
        seed=seed,
    )
    
    # Generate synthetic environmental data
    log.info("environmental_trainer.generating_data")
    df_train, df_val = generate_train_val_split(
        days=data_days,
        validation_split=validation_split,
        seed=seed,
    )
    
    describe_environmental_data(df_train, "Training")
    describe_environmental_data(df_val, "Validation")
    
    # Initialize model
    model = EnvironmentalMonitoringModel()
    
    # Train model
    log.info("environmental_trainer.training_model")
    model.train(df_environmental=df_train)
    
    # Evaluate model
    log.info("environmental_trainer.evaluating_model")
    val_scores = model.evaluate(df_val)
    
    print(f"\n=== ENVIRONMENTAL MODEL TRAINING RESULTS ===")
    print(f"Training samples: {len(df_train)}")
    print(f"Validation samples: {len(df_val)}")
    print(f"Data period: {data_days} days")
    print(f"Features engineered: {len(model.feature_names)}")
    
    print(f"\nVALIDATION SCORES:")
    for metric, value in sorted(val_scores.items()):
        if "accuracy" in metric:
            print(f"  {metric}: {value:.4f}")
        elif "r2" in metric:
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value:.3f}")
    
    # Sample predictions on validation data
    log.info("environmental_trainer.generating_sample_predictions")
    print(f"\n=== SAMPLE PREDICTIONS ===")
    
    # Select some interesting sample scenarios from validation data
    sample_indices = [
        df_val['weather_pattern'].eq('BLIZZARD').idxmax() if 'BLIZZARD' in df_val['weather_pattern'].values else 0,
        df_val['air_temperature'].idxmin(),  # Coldest
        df_val['wind_speed'].idxmax(),       # Windiest
        df_val['comfort_index'].idxmin() if 'comfort_index' in df_val.columns else 0,  # Most uncomfortable
        len(df_val) // 2,                    # Middle sample
    ]
    
    for i, idx in enumerate(sample_indices):
        if idx >= len(df_val):
            continue
            
        row = df_val.iloc[idx]
        
        # Create current conditions dict
        current_conditions = {
            'air_temperature': row['air_temperature'],
            'ground_temperature': row['ground_temperature'],
            'equipment_temperature': row['equipment_temperature'],
            'wind_speed': row['wind_speed'],
            'wind_direction': row['wind_direction'],
            'humidity': row['humidity'],
            'pressure': row['pressure'],
            'visibility': row['visibility'],
            'snow_accumulation': row['snow_accumulation'],
        }
        
        # Get historical context (previous 24 hours)
        start_idx = max(0, idx - 24)
        historical_data = df_val.iloc[start_idx:idx+1].copy()
        
        try:
            pred = model.predict(
                current_conditions=current_conditions,
                historical_data=historical_data,
            )
            
            print(f"\nSample {i+1}: {row['timestamp'].strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"  Actual weather: {row['weather_pattern']}")
            print(f"  Predicted weather: {pred.weather_pattern} (confidence: {pred.weather_confidence:.3f})")
            print(f"  Current temp: {current_conditions['air_temperature']:.1f}°C")
            print(f"  Forecast temp: {pred.forecasted_conditions.get('air_temperature', 0):.1f}°C")
            print(f"  Wind: {current_conditions['wind_speed']:.1f} m/s")
            print(f"  Alert level: {pred.alert_level} ({pred.risk_assessment} risk)")
            print(f"  Active alerts: {pred.active_alerts}")
            print(f"  Equipment stress: {pred.equipment_stress:.3f}")
            print(f"  Comfort index: {pred.comfort_index:.1f}")
            print(f"  Recommendations: {pred.recommendations[0] if pred.recommendations else 'None'}")
            
        except Exception as e:
            log.warning(f"environmental_trainer.prediction_error", sample=i, error=str(e))
            print(f"\nSample {i+1}: Error in prediction - {str(e)}")
    
    # Test extreme scenarios
    print(f"\n=== EXTREME SCENARIO TESTS ===")
    
    extreme_scenarios = [
        {
            "name": "Extreme Blizzard",
            "conditions": {
                'air_temperature': -45.0,
                'ground_temperature': -35.0,
                'equipment_temperature': -5.0,
                'wind_speed': 60.0,
                'wind_direction': 270.0,
                'humidity': 95.0,
                'pressure': 960.0,
                'visibility': 50.0,
                'snow_accumulation': 150.0,
            }
        },
        {
            "name": "Calm Clear Day",
            "conditions": {
                'air_temperature': -2.0,
                'ground_temperature': -8.0,
                'equipment_temperature': 15.0,
                'wind_speed': 3.0,
                'wind_direction': 180.0,
                'humidity': 60.0,
                'pressure': 1015.0,
                'visibility': 15000.0,
                'snow_accumulation': 20.0,
            }
        },
        {
            "name": "Equipment Stress Test",
            "conditions": {
                'air_temperature': -38.0,
                'ground_temperature': -42.0,
                'equipment_temperature': -2.0,
                'wind_speed': 25.0,
                'wind_direction': 225.0,
                'humidity': 45.0,
                'pressure': 975.0,
                'visibility': 2000.0,
                'snow_accumulation': 80.0,
            }
        }
    ]
    
    for scenario in extreme_scenarios:
        try:
            pred = model.predict(current_conditions=scenario["conditions"])
            
            print(f"\n{scenario['name']}:")
            print(f"  Weather pattern: {pred.weather_pattern} (confidence: {pred.weather_confidence:.3f})")
            print(f"  Alert level: {pred.alert_level} ({pred.risk_assessment} risk)")
            print(f"  Active alerts: {len(pred.active_alerts)} alerts")
            print(f"  Equipment stress: {pred.equipment_stress:.3f}")
            print(f"  Comfort index: {pred.comfort_index:.1f}")
            if pred.active_alerts:
                print(f"  Top alerts: {pred.active_alerts[:3]}")
            
        except Exception as e:
            log.warning(f"environmental_trainer.extreme_scenario_error", scenario=scenario["name"], error=str(e))
            print(f"\n{scenario['name']}: Error - {str(e)}")
    
    # Save model
    log.info("environmental_trainer.saving_model")
    model.save(
        val_scores=val_scores,
        n_training_samples=len(df_train),
        notes=notes,
    )
    
    print(f"\n=== MODEL SAVED ===")
    print(f"Model: environmental_monitoring_v1")
    print(f"Sub-models trained: {sum([
        model.weather_classifier is not None,
        model.temperature_forecaster is not None,
        model.wind_forecaster is not None,
        model.humidity_forecaster is not None,
        model.pressure_forecaster is not None,
        model.equipment_stress_model is not None,
        model.comfort_index_model is not None,
    ])}")
    
    # Print key performance metrics
    if 'weather_pattern_accuracy' in val_scores:
        print(f"Weather classification accuracy: {val_scores['weather_pattern_accuracy']:.3f}")
    if 'equipment_stress_r2' in val_scores:
        print(f"Equipment stress R²: {val_scores['equipment_stress_r2']:.3f}")
    if 'air_temperature_future_mae' in val_scores:
        print(f"Temperature forecast MAE: {val_scores['air_temperature_future_mae']:.2f}°C")
    
    return model

def _parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train environmental monitoring model"
    )
    parser.add_argument(
        "--data-days",
        type=int,
        default=365,
        help="Days of synthetic data to generate (default: 365)"
    )
    parser.add_argument(
        "--validation-split",
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Training notes to save with model"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    
    model = run_environmental_training(
        data_days=args.data_days,
        validation_split=args.validation_split,
        seed=args.seed,
        notes=args.notes,
    )
    
    log.info("environmental_trainer.completed")