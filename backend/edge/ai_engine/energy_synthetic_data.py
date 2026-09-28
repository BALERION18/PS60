"""
Synthetic data generation for energy optimization model.

Generates realistic Antarctic power system scenarios including:
- Solar panel efficiency (seasonal, weather-dependent)
- Wind turbine output (Antarctic wind patterns)
- Generator fuel consumption and efficiency
- Power demand from station operations
- Battery state and charging/discharging cycles
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
import structlog

log = structlog.get_logger(__name__)

# Antarctic power system constants
SOLAR_PANEL_CAPACITY_KW = 50.0  # Total solar capacity
WIND_TURBINE_CAPACITY_KW = 30.0  # Total wind capacity
GENERATOR_CAPACITY_KW = 100.0   # Backup generator capacity
BATTERY_CAPACITY_KWH = 200.0    # Battery storage capacity

# Seasonal parameters for Antarctica
SOLAR_EFFICIENCY_SUMMER = 0.85  # Peak summer efficiency
SOLAR_EFFICIENCY_WINTER = 0.15  # Minimal winter sun
WIND_SPEED_AVG_SUMMER = 12.0    # m/s average summer wind
WIND_SPEED_AVG_WINTER = 18.0    # m/s average winter wind

# Power demand profiles (kW)
BASE_LOAD_KW = 25.0             # Minimum station power
HEATING_LOAD_WINTER_KW = 45.0   # Additional heating in winter
RESEARCH_EQUIPMENT_KW = 15.0    # Variable research load

# Default parameters
DEFAULT_DAYS = 365
DEFAULT_TIMESTEPS_PER_DAY = 24  # Hourly data
DEFAULT_NOISE_STD = 0.05
DEFAULT_VALIDATION_SPLIT = 0.2

def _antarctic_solar_efficiency(day_of_year: int) -> float:
    """Calculate solar panel efficiency based on Antarctic seasonal patterns."""
    # Antarctic summer: Oct-Feb (days 274-365, 1-59)
    # Antarctic winter: Apr-Sep (days 90-273)
    
    if day_of_year <= 59 or day_of_year >= 274:  # Summer
        return SOLAR_EFFICIENCY_SUMMER * (0.8 + 0.2 * np.sin((day_of_year - 274) * 2 * np.pi / 365))
    elif 90 <= day_of_year <= 273:  # Winter
        return SOLAR_EFFICIENCY_WINTER * (0.5 + 0.5 * np.sin((day_of_year - 90) * np.pi / 183))
    else:  # Transition periods
        transition_factor = 0.4 + 0.2 * np.sin(day_of_year * 2 * np.pi / 365)
        return (SOLAR_EFFICIENCY_SUMMER + SOLAR_EFFICIENCY_WINTER) * 0.5 * transition_factor

def _antarctic_wind_speed(day_of_year: int, hour_of_day: int, rng: np.random.Generator) -> float:
    """Generate realistic Antarctic wind speed with seasonal and diurnal patterns."""
    # Base seasonal pattern
    if day_of_year <= 59 or day_of_year >= 274:  # Summer
        base_speed = WIND_SPEED_AVG_SUMMER
    else:  # Winter - stronger winds
        base_speed = WIND_SPEED_AVG_WINTER
    
    # Diurnal variation (wind often stronger during day)
    diurnal_factor = 1.0 + 0.3 * np.sin((hour_of_day - 6) * np.pi / 12)
    
    # Random variation
    noise = rng.normal(0, base_speed * 0.2)
    
    wind_speed = base_speed * diurnal_factor + noise
    return max(0.0, wind_speed)  # Wind speed can't be negative

def _wind_power_output(wind_speed: float) -> float:
    """Calculate wind turbine power output from wind speed (simplified model)."""
    if wind_speed < 3.0:  # Cut-in speed
        return 0.0
    elif wind_speed > 25.0:  # Cut-out speed (safety)
        return 0.0
    elif wind_speed > 12.0:  # Rated speed
        return WIND_TURBINE_CAPACITY_KW
    else:  # Power curve approximation
        return WIND_TURBINE_CAPACITY_KW * (wind_speed - 3.0) / 9.0

def _power_demand(day_of_year: int, hour_of_day: int, rng: np.random.Generator) -> float:
    """Generate realistic power demand with seasonal and diurnal patterns."""
    # Base load is always present
    demand = BASE_LOAD_KW
    
    # Heating load (higher in winter)
    if day_of_year <= 59 or day_of_year >= 274:  # Summer
        heating_factor = 0.3
    else:  # Winter
        heating_factor = 1.0 + 0.5 * np.sin((day_of_year - 90) * np.pi / 183)
    
    demand += HEATING_LOAD_WINTER_KW * heating_factor
    
    # Research equipment (higher during day)
    research_factor = 0.5 + 0.5 * np.sin((hour_of_day - 6) * np.pi / 12)
    if 6 <= hour_of_day <= 22:  # Active research hours
        research_factor *= 1.5
    
    demand += RESEARCH_EQUIPMENT_KW * research_factor
    
    # Random variation
    demand += rng.normal(0, demand * 0.1)
    
    return max(5.0, demand)  # Minimum demand

def _battery_dynamics(
    current_soc: float,
    power_balance: float,
    dt_hours: float = 1.0
) -> float:
    """Update battery state of charge based on power balance."""
    # Charging/discharging efficiency
    efficiency = 0.95 if power_balance > 0 else 1.0 / 0.95
    
    # Energy change in kWh
    energy_change = power_balance * dt_hours * efficiency
    
    # New SOC (0-1 range)
    new_soc = current_soc + energy_change / BATTERY_CAPACITY_KWH
    
    return np.clip(new_soc, 0.0, 1.0)

def generate_energy_timeseries(
    days: int = DEFAULT_DAYS,
    timesteps_per_day: int = DEFAULT_TIMESTEPS_PER_DAY,
    start_date: Optional[datetime] = None,
    noise_std: float = DEFAULT_NOISE_STD,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate synthetic energy system time series data.
    
    Returns DataFrame with columns:
    - timestamp: DateTime index
    - solar_efficiency: Solar panel efficiency (0-1)
    - wind_speed: Wind speed (m/s)
    - solar_power: Solar power generation (kW)
    - wind_power: Wind power generation (kW)
    - power_demand: Station power demand (kW)
    - renewable_power: Total renewable power (kW)
    - power_balance: Power balance before generator (kW, negative = deficit)
    - battery_soc: Battery state of charge (0-1)
    - generator_power: Generator power output (kW)
    - fuel_consumption: Generator fuel consumption (L/h)
    - total_power: Total power available (kW)
    - power_shortage: Unmet demand (kW)
    """
    if start_date is None:
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    rng = np.random.Generator(np.random.PCG64(seed))
    
    total_timesteps = days * timesteps_per_day
    dt_hours = 24.0 / timesteps_per_day
    
    log.info(
        "energy_synthetic.generating_timeseries",
        days=days,
        timesteps_per_day=timesteps_per_day,
        total_timesteps=total_timesteps,
        dt_hours=dt_hours,
    )
    
    # Initialize arrays
    timestamps = []
    solar_efficiency = np.zeros(total_timesteps)
    wind_speed = np.zeros(total_timesteps)
    solar_power = np.zeros(total_timesteps)
    wind_power = np.zeros(total_timesteps)
    power_demand = np.zeros(total_timesteps)
    renewable_power = np.zeros(total_timesteps)
    power_balance = np.zeros(total_timesteps)
    battery_soc = np.zeros(total_timesteps)
    generator_power = np.zeros(total_timesteps)
    fuel_consumption = np.zeros(total_timesteps)
    total_power = np.zeros(total_timesteps)
    power_shortage = np.zeros(total_timesteps)
    
    # Initialize battery SOC
    current_soc = 0.5  # Start at 50% charge
    
    for i in range(total_timesteps):
        current_time = start_date + timedelta(hours=i * dt_hours)
        timestamps.append(current_time)
        
        day_of_year = current_time.timetuple().tm_yday
        hour_of_day = current_time.hour
        
        # Generate renewable energy sources
        solar_eff = _antarctic_solar_efficiency(day_of_year)
        ws = _antarctic_wind_speed(day_of_year, hour_of_day, rng)
        
        # Solar power (depends on time of day for daylight)
        daylight_factor = max(0.0, np.sin((hour_of_day - 6) * np.pi / 12))
        if day_of_year <= 59 or day_of_year >= 274:  # Antarctic summer
            daylight_factor *= 1.0  # Long days
        else:  # Winter
            daylight_factor *= 0.2  # Short/no daylight
        
        sp = SOLAR_PANEL_CAPACITY_KW * solar_eff * daylight_factor
        wp = _wind_power_output(ws)
        
        # Power demand
        pd_val = _power_demand(day_of_year, hour_of_day, rng)
        
        # Renewable power total
        rp = sp + wp
        
        # Power balance before generator
        pb_before_gen = rp - pd_val
        
        # Battery dynamics
        current_soc = _battery_dynamics(current_soc, pb_before_gen, dt_hours)
        
        # Generator decision (simplified logic)
        if current_soc < 0.2 or pb_before_gen < -20:  # Low battery or high deficit
            gen_power = min(GENERATOR_CAPACITY_KW, max(0, -pb_before_gen + 10))
        else:
            gen_power = 0.0
        
        # Fuel consumption (L/h) - simplified linear model
        fuel_rate = gen_power * 0.3 + 2.0 if gen_power > 0 else 0.0  # Includes idle consumption
        
        # Total available power
        total_pow = rp + gen_power
        
        # Power shortage
        shortage = max(0.0, pd_val - total_pow)
        
        # Store values
        solar_efficiency[i] = solar_eff
        wind_speed[i] = ws
        solar_power[i] = sp
        wind_power[i] = wp
        power_demand[i] = pd_val
        renewable_power[i] = rp
        power_balance[i] = pb_before_gen
        battery_soc[i] = current_soc
        generator_power[i] = gen_power
        fuel_consumption[i] = fuel_rate
        total_power[i] = total_pow
        power_shortage[i] = shortage
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'solar_efficiency': solar_efficiency,
        'wind_speed': wind_speed,
        'solar_power': solar_power,
        'wind_power': wind_power,
        'power_demand': power_demand,
        'renewable_power': renewable_power,
        'power_balance': power_balance,
        'battery_soc': battery_soc,
        'generator_power': generator_power,
        'fuel_consumption': fuel_consumption,
        'total_power': total_power,
        'power_shortage': power_shortage,
    })
    
    # Add noise to make it more realistic
    noise_cols = ['solar_power', 'wind_power', 'power_demand']
    for col in noise_cols:
        noise = rng.normal(0, df[col].std() * noise_std, len(df))
        df[col] = np.maximum(0.0, df[col] + noise)
    
    return df

def generate_train_val_split(
    days: int = DEFAULT_DAYS,
    validation_split: float = DEFAULT_VALIDATION_SPLIT,
    seed: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate training and validation datasets."""
    val_days = int(days * validation_split)
    train_days = days - val_days
    
    log.info(
        "energy_synthetic.generating_split",
        total_days=days,
        train_days=train_days,
        val_days=val_days,
    )
    
    # Generate training data (first part of year)
    df_train = generate_energy_timeseries(
        days=train_days,
        seed=seed,
    )
    
    # Generate validation data (later part of year)
    val_start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=train_days)
    df_val = generate_energy_timeseries(
        days=val_days,
        start_date=val_start,
        seed=seed + 1000 if seed is not None else None,
    )
    
    return df_train, df_val

def describe_energy_data(df: pd.DataFrame, name: str = "energy_data") -> None:
    """Print descriptive statistics for energy dataset."""
    print(f"\n=== {name.upper()} DATASET SUMMARY ===")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Total timesteps: {len(df)}")
    print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    
    print(f"\nPOWER GENERATION:")
    print(f"  Solar power: {df['solar_power'].mean():.2f} ± {df['solar_power'].std():.2f} kW")
    print(f"  Wind power: {df['wind_power'].mean():.2f} ± {df['wind_power'].std():.2f} kW")
    print(f"  Generator power: {df['generator_power'].mean():.2f} ± {df['generator_power'].std():.2f} kW")
    print(f"  Renewable contribution: {df['renewable_power'].sum() / df['total_power'].sum() * 100:.1f}%")
    
    print(f"\nPOWER CONSUMPTION:")
    print(f"  Average demand: {df['power_demand'].mean():.2f} ± {df['power_demand'].std():.2f} kW")
    print(f"  Peak demand: {df['power_demand'].max():.2f} kW")
    print(f"  Total consumption: {df['power_demand'].sum():.0f} kWh")
    
    print(f"\nSYSTEM EFFICIENCY:")
    print(f"  Average battery SOC: {df['battery_soc'].mean():.2f} ± {df['battery_soc'].std():.2f}")
    print(f"  Power shortage events: {(df['power_shortage'] > 0).sum()} / {len(df)}")
    print(f"  Generator runtime: {(df['generator_power'] > 0).sum() / len(df) * 100:.1f}% of time")
    print(f"  Total fuel consumption: {df['fuel_consumption'].sum():.0f} L")
    
    print("="*50)

if __name__ == "__main__":
    # Generate sample data for testing
    df_train, df_val = generate_train_val_split(days=90, seed=42)
    
    describe_energy_data(df_train, "Training")
    describe_energy_data(df_val, "Validation")