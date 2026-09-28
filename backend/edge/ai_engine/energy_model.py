"""
Energy Optimization Model for Antarctic power management.

Uses Q-Learning (tabular RL) to optimize generator usage, battery charging,
and load management to minimize fuel consumption while maintaining power reliability.

State space: [battery_level, renewable_power, demand_level, time_of_day]
Action space: [generator_off, generator_low, generator_medium, generator_high]
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any
import structlog
import warnings
import joblib
from pathlib import Path

from edge.ai_engine.model_store import ModelStore, ModelMetadata, get_model_store, utcnow_iso

log = structlog.get_logger(__name__)

# Model configuration
MODEL_NAME = "energy_optimization"
MODEL_VERSION = "v1"

# Q-Learning parameters
DEFAULT_LEARNING_RATE = 0.1
DEFAULT_DISCOUNT_FACTOR = 0.95
DEFAULT_EPSILON = 0.1  # Exploration rate
DEFAULT_EPSILON_DECAY = 0.995
DEFAULT_MIN_EPSILON = 0.01

# State space discretization
BATTERY_BINS = 10  # 0-100% in 10% increments
RENEWABLE_BINS = 8  # Power levels
DEMAND_BINS = 6    # Demand levels
TIME_BINS = 24     # Hours of day

# Action space
GENERATOR_ACTIONS = ["OFF", "LOW", "MEDIUM", "HIGH"]
N_ACTIONS = len(GENERATOR_ACTIONS)

# Power system parameters
GENERATOR_CAPACITY_KW = 100.0
GENERATOR_LEVELS = [0.0, 25.0, 50.0, 100.0]  # OFF, LOW, MEDIUM, HIGH
FUEL_RATES = [0.0, 8.0, 18.0, 35.0]  # L/h for each generator level
BATTERY_CAPACITY_KWH = 200.0

class EnergyState:
    """Represents the current state of the energy system."""
    
    def __init__(
        self,
        battery_soc: float,
        renewable_power: float,
        power_demand: float,
        hour_of_day: int,
    ):
        self.battery_soc = battery_soc  # 0-1
        self.renewable_power = renewable_power  # kW
        self.power_demand = power_demand  # kW
        self.hour_of_day = hour_of_day  # 0-23
    
    def to_discrete_state(self) -> Tuple[int, int, int, int]:
        """Convert continuous state to discrete state indices."""
        battery_bin = min(BATTERY_BINS - 1, int(self.battery_soc * BATTERY_BINS))
        renewable_bin = min(RENEWABLE_BINS - 1, int(self.renewable_power / 20.0))  # 0-160kW range
        demand_bin = min(DEMAND_BINS - 1, int(self.power_demand / 20.0))  # 0-120kW range
        time_bin = self.hour_of_day
        
        return (battery_bin, renewable_bin, demand_bin, time_bin)
    
    def __str__(self) -> str:
        return f"EnergyState(battery={self.battery_soc:.2f}, renewable={self.renewable_power:.1f}kW, demand={self.power_demand:.1f}kW, hour={self.hour_of_day})"

class EnergyAction:
    """Represents an action taken by the energy optimization agent."""
    
    def __init__(self, generator_level: str):
        if generator_level not in GENERATOR_ACTIONS:
            raise ValueError(f"Invalid generator level: {generator_level}")
        self.generator_level = generator_level
        self.action_index = GENERATOR_ACTIONS.index(generator_level)
    
    @property
    def generator_power(self) -> float:
        """Get generator power output for this action."""
        return GENERATOR_LEVELS[self.action_index]
    
    @property
    def fuel_rate(self) -> float:
        """Get fuel consumption rate for this action."""
        return FUEL_RATES[self.action_index]
    
    def __str__(self) -> str:
        return f"EnergyAction({self.generator_level}, {self.generator_power}kW, {self.fuel_rate}L/h)"

class EnergyOptimizationPrediction:
    """Output from energy optimization model."""
    
    def __init__(
        self,
        current_state: EnergyState,
        recommended_action: EnergyAction,
        q_values: Dict[str, float],
        confidence: float,
        expected_reward: float,
        system_status: str,
        fuel_savings_pct: float,
        risk_assessment: str,
    ):
        self.current_state = current_state
        self.recommended_action = recommended_action
        self.q_values = q_values
        self.confidence = confidence
        self.expected_reward = expected_reward
        self.system_status = system_status
        self.fuel_savings_pct = fuel_savings_pct
        self.risk_assessment = risk_assessment
        self.predicted_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": {
                "battery_soc": self.current_state.battery_soc,
                "renewable_power": self.current_state.renewable_power,
                "power_demand": self.current_state.power_demand,
                "hour_of_day": self.current_state.hour_of_day,
            },
            "recommended_action": {
                "generator_level": self.recommended_action.generator_level,
                "generator_power": self.recommended_action.generator_power,
                "fuel_rate": self.recommended_action.fuel_rate,
            },
            "q_values": self.q_values,
            "confidence": self.confidence,
            "expected_reward": self.expected_reward,
            "system_status": self.system_status,
            "fuel_savings_pct": self.fuel_savings_pct,
            "risk_assessment": self.risk_assessment,
            "predicted_at": self.predicted_at,
        }

class EnergyOptimizationModel:
    """Q-Learning based energy optimization model.
    
    Usage — training:
        model = EnergyOptimizationModel()
        model.train(df_energy_data)
        model.evaluate(df_val_data)
        model.save()
    
    Usage — inference:
        model = EnergyOptimizationModel.load()
        pred = model.predict(
            battery_soc=0.4,
            renewable_power=35.0,
            power_demand=45.0,
            hour_of_day=14
        )
    """
    
    def __init__(
        self,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        discount_factor: float = DEFAULT_DISCOUNT_FACTOR,
        epsilon: float = DEFAULT_EPSILON,
    ):
        # Q-table: [battery_bin, renewable_bin, demand_bin, time_bin, action]
        self.q_table = np.zeros((BATTERY_BINS, RENEWABLE_BINS, DEMAND_BINS, TIME_BINS, N_ACTIONS))
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.initial_epsilon = epsilon
        
        # Training stats
        self.training_episodes = 0
        self.total_rewards = []
        self.fuel_consumptions = []
        self.power_shortage_counts = []
        
        # Model persistence
        self._metadata: Optional[ModelMetadata] = None
        self._store: ModelStore = get_model_store()
    
    def _calculate_reward(
        self,
        state: EnergyState,
        action: EnergyAction,
        next_state: EnergyState,
        power_shortage: float,
    ) -> float:
        """Calculate reward for state-action pair."""
        reward = 0.0
        
        # Penalty for fuel consumption (primary objective)
        fuel_penalty = -action.fuel_rate * 0.1
        reward += fuel_penalty
        
        # Large penalty for power shortages (reliability constraint)
        shortage_penalty = -power_shortage * 10.0
        reward += shortage_penalty
        
        # Bonus for maintaining good battery level
        if 0.3 <= next_state.battery_soc <= 0.8:
            reward += 5.0
        elif next_state.battery_soc < 0.2:
            reward -= 20.0  # Critical low battery
        
        # Small bonus for using renewable energy efficiently
        renewable_bonus = min(5.0, state.renewable_power * 0.1)
        reward += renewable_bonus
        
        # Penalty for unnecessary generator use when renewables are sufficient
        if action.generator_power > 0 and state.renewable_power > state.power_demand:
            reward -= 3.0
        
        return reward
    
    def _simulate_step(
        self,
        state: EnergyState,
        action: EnergyAction,
        dt_hours: float = 1.0,
    ) -> Tuple[EnergyState, float, float]:
        """Simulate one timestep of the energy system."""
        # Power balance
        total_supply = state.renewable_power + action.generator_power
        power_shortage = max(0.0, state.power_demand - total_supply)
        
        # Battery dynamics (simplified)
        power_balance = total_supply - state.power_demand
        efficiency = 0.95 if power_balance > 0 else 1.0 / 0.95
        energy_change = power_balance * dt_hours * efficiency
        new_soc = np.clip(
            state.battery_soc + energy_change / BATTERY_CAPACITY_KWH,
            0.0, 1.0
        )
        
        # Create next state (assume renewable and demand stay same for simplicity)
        next_state = EnergyState(
            battery_soc=new_soc,
            renewable_power=state.renewable_power,
            power_demand=state.power_demand,
            hour_of_day=(state.hour_of_day + 1) % 24,
        )
        
        # Calculate reward
        reward = self._calculate_reward(state, action, next_state, power_shortage)
        
        return next_state, reward, power_shortage
    
    def _get_action(self, state: EnergyState, training: bool = False) -> EnergyAction:
        """Get action using epsilon-greedy policy."""
        state_indices = state.to_discrete_state()
        
        if training and np.random.random() < self.epsilon:
            # Explore: random action
            action_index = np.random.randint(N_ACTIONS)
        else:
            # Exploit: best action
            q_values = self.q_table[state_indices]
            action_index = np.argmax(q_values)
        
        return EnergyAction(GENERATOR_ACTIONS[action_index])
    
    def train(
        self,
        df_energy: pd.DataFrame,
        episodes: int = 1000,
        max_steps_per_episode: int = 168,  # 1 week
    ) -> None:
        """Train the Q-learning model on energy system data."""
        log.info(
            "energy_model.training_start",
            episodes=episodes,
            max_steps_per_episode=max_steps_per_episode,
            q_table_shape=self.q_table.shape,
        )
        
        # Reset training stats
        self.total_rewards = []
        self.fuel_consumptions = []
        self.power_shortage_counts = []
        
        for episode in range(episodes):
            # Sample random starting point in data
            start_idx = np.random.randint(len(df_energy) - max_steps_per_episode)
            
            episode_reward = 0.0
            episode_fuel = 0.0
            episode_shortages = 0
            
            # Initialize state from data
            row = df_energy.iloc[start_idx]
            state = EnergyState(
                battery_soc=row['battery_soc'],
                renewable_power=row['renewable_power'],
                power_demand=row['power_demand'],
                hour_of_day=row['timestamp'].hour,
            )
            
            for step in range(max_steps_per_episode):
                if start_idx + step >= len(df_energy):
                    break
                
                # Get action
                action = self._get_action(state, training=True)
                
                # Update state from next data point
                next_row = df_energy.iloc[start_idx + step + 1] if start_idx + step + 1 < len(df_energy) else row
                next_state = EnergyState(
                    battery_soc=next_row['battery_soc'],
                    renewable_power=next_row['renewable_power'],
                    power_demand=next_row['power_demand'],
                    hour_of_day=next_row['timestamp'].hour,
                )
                
                # Simulate and get reward
                _, reward, power_shortage = self._simulate_step(state, action)
                
                # Q-learning update
                state_indices = state.to_discrete_state()
                next_state_indices = next_state.to_discrete_state()
                
                current_q = self.q_table[state_indices + (action.action_index,)]
                max_next_q = np.max(self.q_table[next_state_indices])
                
                td_target = reward + self.discount_factor * max_next_q
                td_error = td_target - current_q
                self.q_table[state_indices + (action.action_index,)] += self.learning_rate * td_error
                
                # Update episode stats
                episode_reward += reward
                episode_fuel += action.fuel_rate
                if power_shortage > 0:
                    episode_shortages += 1
                
                state = next_state
            
            # Decay epsilon
            self.epsilon = max(DEFAULT_MIN_EPSILON, self.epsilon * DEFAULT_EPSILON_DECAY)
            
            # Store episode stats
            self.total_rewards.append(episode_reward)
            self.fuel_consumptions.append(episode_fuel)
            self.power_shortage_counts.append(episode_shortages)
            
            if episode % 100 == 0:
                avg_reward = np.mean(self.total_rewards[-100:]) if len(self.total_rewards) >= 100 else np.mean(self.total_rewards)
                log.info(
                    "energy_model.training_progress",
                    episode=episode,
                    avg_reward=round(avg_reward, 2),
                    epsilon=round(self.epsilon, 3),
                    avg_fuel=round(np.mean(self.fuel_consumptions[-100:]), 2),
                )
        
        self.training_episodes = episodes
        
        log.info(
            "energy_model.training_done",
            total_episodes=episodes,
            final_epsilon=round(self.epsilon, 3),
            avg_final_reward=round(np.mean(self.total_rewards[-100:]), 2),
        )
    
    def predict(
        self,
        battery_soc: float,
        renewable_power: float,
        power_demand: float,
        hour_of_day: int,
    ) -> EnergyOptimizationPrediction:
        """Predict optimal generator action for given state."""
        state = EnergyState(battery_soc, renewable_power, power_demand, hour_of_day)
        state_indices = state.to_discrete_state()
        
        # Get Q-values for all actions
        q_values_array = self.q_table[state_indices]
        q_values = {
            GENERATOR_ACTIONS[i]: float(q_values_array[i])
            for i in range(N_ACTIONS)
        }
        
        # Best action
        best_action_index = np.argmax(q_values_array)
        recommended_action = EnergyAction(GENERATOR_ACTIONS[best_action_index])
        
        # Confidence based on Q-value spread
        q_std = np.std(q_values_array)
        confidence = 1.0 - min(1.0, q_std / 10.0)  # Normalize to 0-1
        
        # Expected reward
        expected_reward = float(q_values_array[best_action_index])
        
        # System status assessment
        if battery_soc < 0.2:
            system_status = "CRITICAL_BATTERY"
        elif power_demand > renewable_power + 50:  # High deficit
            system_status = "HIGH_DEMAND"
        elif renewable_power > power_demand * 1.5:  # Excess renewable
            system_status = "SURPLUS_RENEWABLE"
        else:
            system_status = "NORMAL"
        
        # Fuel savings estimate (compared to always running generator at medium)
        baseline_fuel = FUEL_RATES[2]  # MEDIUM level
        actual_fuel = recommended_action.fuel_rate
        fuel_savings_pct = (baseline_fuel - actual_fuel) / baseline_fuel * 100 if baseline_fuel > 0 else 0.0
        
        # Risk assessment
        if battery_soc < 0.15:
            risk_assessment = "HIGH"
        elif battery_soc < 0.3 and renewable_power < power_demand * 0.5:
            risk_assessment = "MEDIUM"
        else:
            risk_assessment = "LOW"
        
        return EnergyOptimizationPrediction(
            current_state=state,
            recommended_action=recommended_action,
            q_values=q_values,
            confidence=confidence,
            expected_reward=expected_reward,
            system_status=system_status,
            fuel_savings_pct=fuel_savings_pct,
            risk_assessment=risk_assessment,
        )
    
    def evaluate(self, df_val: pd.DataFrame) -> Dict[str, float]:
        """Evaluate model performance on validation data."""
        log.info("energy_model.evaluation_start", n_samples=len(df_val))
        
        total_fuel_actual = 0.0
        total_fuel_baseline = 0.0
        total_shortages = 0
        correct_actions = 0
        total_rewards = []
        
        for i in range(len(df_val) - 1):
            row = df_val.iloc[i]
            state = EnergyState(
                battery_soc=row['battery_soc'],
                renewable_power=row['renewable_power'],
                power_demand=row['power_demand'],
                hour_of_day=row['timestamp'].hour,
            )
            
            # Get model prediction
            pred = self.predict(
                state.battery_soc,
                state.renewable_power,
                state.power_demand,
                state.hour_of_day,
            )
            
            # Simulate step
            _, reward, power_shortage = self._simulate_step(state, pred.recommended_action)
            
            # Accumulate metrics
            total_fuel_actual += pred.recommended_action.fuel_rate
            total_fuel_baseline += FUEL_RATES[2]  # Always medium
            if power_shortage > 0:
                total_shortages += 1
            total_rewards.append(reward)
            
            # Check if action makes sense (heuristic)
            if state.battery_soc < 0.3 and pred.recommended_action.generator_power > 0:
                correct_actions += 1
            elif state.battery_soc > 0.7 and state.renewable_power > state.power_demand:
                if pred.recommended_action.generator_power == 0:
                    correct_actions += 1
        
        fuel_savings = (total_fuel_baseline - total_fuel_actual) / total_fuel_baseline * 100
        shortage_rate = total_shortages / len(df_val) * 100
        action_accuracy = correct_actions / len(df_val) * 100
        avg_reward = np.mean(total_rewards)
        
        metrics = {
            "fuel_savings_pct": fuel_savings,
            "power_shortage_rate_pct": shortage_rate,
            "action_accuracy_pct": action_accuracy,
            "avg_reward": avg_reward,
            "total_fuel_saved_L": total_fuel_baseline - total_fuel_actual,
        }
        
        log.info(
            "energy_model.evaluation_done",
            fuel_savings_pct=round(fuel_savings, 2),
            shortage_rate_pct=round(shortage_rate, 3),
            action_accuracy_pct=round(action_accuracy, 2),
            avg_reward=round(avg_reward, 2),
        )
        
        return metrics
    
    def save(
        self,
        val_scores: Optional[Dict[str, float]] = None,
        n_training_episodes: int = 0,
        notes: str = "",
    ) -> None:
        """Save model to disk."""
        payload = {
            "q_table": self.q_table,
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "initial_epsilon": self.initial_epsilon,
            "training_episodes": self.training_episodes,
            "total_rewards": self.total_rewards[-100:],  # Last 100 episodes
            "fuel_consumptions": self.fuel_consumptions[-100:],
        }
        
        metadata = ModelMetadata(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            trained_at=utcnow_iso(),
            algorithm="Q-Learning",
            feature_names=["battery_soc", "renewable_power", "power_demand", "hour_of_day"],
            n_features=4,
            val_scores=val_scores or {},
            hyperparameters={
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon_initial": self.initial_epsilon,
                "q_table_shape": list(self.q_table.shape),
            },
            n_training_samples=n_training_episodes,
            notes=notes,
        )
        
        self._store.save(payload, metadata)
        self._metadata = metadata
        
        log.info(
            "energy_model.saved",
            model_name=MODEL_NAME,
            version=MODEL_VERSION,
            q_table_shape=self.q_table.shape,
        )
    
    @classmethod
    def load(cls, version: str = MODEL_VERSION) -> "EnergyOptimizationModel":
        """Load model from disk."""
        store = get_model_store()
        payload, metadata = store.load(MODEL_NAME, version)
        
        model = cls()
        model.q_table = payload["q_table"]
        model.learning_rate = payload["learning_rate"]
        model.discount_factor = payload["discount_factor"]
        model.initial_epsilon = payload["initial_epsilon"]
        model.training_episodes = payload.get("training_episodes", 0)
        model.total_rewards = payload.get("total_rewards", [])
        model.fuel_consumptions = payload.get("fuel_consumptions", [])
        model._metadata = metadata
        
        log.info(
            "energy_model.loaded",
            model_name=MODEL_NAME,
            version=version,
            trained_at=metadata.trained_at,
        )
        
        return model
    
    @classmethod
    def load_or_none(cls, version: str = MODEL_VERSION) -> Optional["EnergyOptimizationModel"]:
        """Load model or return None if not found."""
        try:
            return cls.load(version)
        except Exception as e:
            log.warning("energy_model.load_failed", error=str(e))
            return None
    
    @property
    def is_loaded(self) -> bool:
        return self._metadata is not None
    
    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata

def get_action_description(action: EnergyAction, state: EnergyState) -> str:
    """Get human-readable description of recommended action."""
    descriptions = {
        "OFF": "Turn off generator (rely on renewables + battery)",
        "LOW": "Run generator at low power (25kW)",
        "MEDIUM": "Run generator at medium power (50kW)",
        "HIGH": "Run generator at high power (100kW)",
    }
    
    base_desc = descriptions[action.generator_level]
    
    # Add context
    if state.battery_soc < 0.3:
        context = " - Battery needs charging"
    elif state.renewable_power > state.power_demand:
        context = " - Renewable surplus available"
    elif state.power_demand > state.renewable_power + 20:
        context = " - High power deficit"
    else:
        context = ""
    
    return base_desc + context