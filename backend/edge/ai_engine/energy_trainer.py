"""
Training script for energy optimization model.

Usage:
    python -m edge.ai_engine.energy_trainer --episodes 2000 --data-days 180
"""

import argparse
import logging
import structlog
from typing import Optional

from edge.ai_engine.energy_synthetic_data import generate_train_val_split, describe_energy_data
from edge.ai_engine.energy_model import EnergyOptimizationModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = structlog.get_logger(__name__)

def run_energy_training(
    episodes: int = 2000,
    data_days: int = 180,
    max_steps_per_episode: int = 168,
    learning_rate: float = 0.1,
    seed: Optional[int] = None,
    notes: str = "",
) -> EnergyOptimizationModel:
    """Run the full energy optimization model training pipeline."""
    
    log.info(
        "energy_trainer.starting",
        episodes=episodes,
        data_days=data_days,
        max_steps_per_episode=max_steps_per_episode,
        learning_rate=learning_rate,
        seed=seed,
    )
    
    # Generate synthetic energy data
    log.info("energy_trainer.generating_data")
    df_train, df_val = generate_train_val_split(
        days=data_days,
        seed=seed,
    )
    
    describe_energy_data(df_train, "Training")
    describe_energy_data(df_val, "Validation")
    
    # Initialize model
    model = EnergyOptimizationModel(learning_rate=learning_rate)
    
    # Train model
    log.info("energy_trainer.training_model")
    model.train(
        df_energy=df_train,
        episodes=episodes,
        max_steps_per_episode=max_steps_per_episode,
    )
    
    # Evaluate model
    log.info("energy_trainer.evaluating_model")
    val_scores = model.evaluate(df_val)
    
    print(f"\n=== ENERGY MODEL TRAINING RESULTS ===")
    print(f"Training episodes: {episodes}")
    print(f"Data period: {data_days} days")
    print(f"Learning rate: {learning_rate}")
    
    print(f"\nVALIDATION SCORES:")
    for metric, value in val_scores.items():
        if "pct" in metric:
            print(f"  {metric}: {value:.2f}%")
        else:
            print(f"  {metric}: {value:.3f}")
    
    # Sample predictions
    log.info("energy_trainer.generating_sample_predictions")
    print(f"\n=== SAMPLE PREDICTIONS ===")
    
    # Sample scenarios
    scenarios = [
        {"battery_soc": 0.2, "renewable_power": 10.0, "power_demand": 50.0, "hour_of_day": 14, "desc": "Low battery, high demand, daytime"},
        {"battery_soc": 0.8, "renewable_power": 60.0, "power_demand": 30.0, "hour_of_day": 12, "desc": "High battery, renewable surplus, noon"},
        {"battery_soc": 0.5, "renewable_power": 5.0, "power_demand": 45.0, "hour_of_day": 2, "desc": "Medium battery, low renewables, night"},
        {"battery_soc": 0.1, "renewable_power": 0.0, "power_demand": 60.0, "hour_of_day": 20, "desc": "Critical battery, no renewables, evening"},
    ]
    
    for scenario in scenarios:
        pred = model.predict(
            battery_soc=scenario["battery_soc"],
            renewable_power=scenario["renewable_power"],
            power_demand=scenario["power_demand"],
            hour_of_day=scenario["hour_of_day"],
        )
        
        print(f"\nScenario: {scenario['desc']}")
        print(f"  State: {scenario['battery_soc']*100:.0f}% battery, {scenario['renewable_power']:.0f}kW renewable, {scenario['power_demand']:.0f}kW demand")
        print(f"  Action: {pred.recommended_action.generator_level} ({pred.recommended_action.generator_power:.0f}kW, {pred.recommended_action.fuel_rate:.1f}L/h)")
        print(f"  System: {pred.system_status}")
        print(f"  Risk: {pred.risk_assessment}")
        print(f"  Confidence: {pred.confidence:.3f}")
        print(f"  Fuel savings: {pred.fuel_savings_pct:.1f}%")
    
    # Save model
    log.info("energy_trainer.saving_model")
    model.save(
        val_scores=val_scores,
        n_training_episodes=episodes,
        notes=notes,
    )
    
    print(f"\n=== MODEL SAVED ===")
    print(f"Model: energy_optimization_v1")
    print(f"Fuel savings potential: {val_scores.get('fuel_savings_pct', 0):.1f}%")
    print(f"Power reliability: {100 - val_scores.get('power_shortage_rate_pct', 0):.1f}%")
    
    return model

def _parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train energy optimization model"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=2000,
        help="Number of training episodes (default: 2000)"
    )
    parser.add_argument(
        "--data-days",
        type=int,
        default=180,
        help="Days of synthetic data to generate (default: 180)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=168,
        help="Maximum steps per episode (default: 168 = 1 week)"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.1,
        help="Q-learning learning rate (default: 0.1)"
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
    
    model = run_energy_training(
        episodes=args.episodes,
        data_days=args.data_days,
        max_steps_per_episode=args.max_steps,
        learning_rate=args.learning_rate,
        seed=args.seed,
        notes=args.notes,
    )
    
    log.info("energy_trainer.completed")