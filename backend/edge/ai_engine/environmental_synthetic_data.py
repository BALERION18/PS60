"""
Synthetic data generation for environmental monitoring model.

Generates realistic Antarctic environmental data including:
- Temperature (air, ground, equipment)
- Wind speed and direction
- Humidity and barometric pressure
- Snow accumulation and visibility
- Weather pattern classification
- Environmental alerts and thresholds
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
import structlog

log = structlog.get_logger(__name__)

# Antarctic environmental constants
TEMP_SUMMER_MEAN = -5.0     # °C average summer temperature
TEMP_WINTER_MEAN = -25.0    # °C average winter temperature
TEMP_DAILY_RANGE = 8.0      # °C daily temperature variation

WIND_SPEED_MEAN = 15.0      # m/s average wind speed
WIND_SPEED_STORM = 35.0     # m/s storm threshold
WIND_DIRECTION_BIAS = 225   # Degrees, prevailing westerly winds

HUMIDITY_BASE = 75.0        # % relative humidity baseline
PRESSURE_BASE = 985.0       # hPa barometric pressure baseline

VISIBILITY_GOOD = 10000     # meters, good visibility
VISIBILITY_POOR = 100       # meters, poor visibility threshold

# Weather patterns
WEATHER_PATTERNS = [
    "CLEAR", "PARTLY_CLOUDY", "OVERCAST", 
    "LIGHT_SNOW", "HEAVY_SNOW", "BLIZZARD",
    "FOG", "STORM"
]

# Default parameters
DEFAULT_DAYS = 365
DEFAULT_TIMESTEPS_PER_DAY = 24  # Hourly data
DEFAULT_NOISE_STD = 0.1
DEFAULT_VALIDATION_SPLIT = 0.2

def _antarctic_temperature(
    day_of_year: int, 
    hour_of_day: int, 
    rng: np.random.Generator
) -> float:
    """Generate realistic Antarctic temperature with seasonal and diurnal patterns."""
    # Seasonal component (Antarctic summer: Oct-Feb, winter: Apr-Sep)
    if day_of_year <= 59 or day_of_year >= 274:  # Summer
        seasonal_temp = TEMP_SUMMER_MEAN
        seasonal_variation = 10.0  # More variable in summer
    else:  # Winter
        seasonal_temp = TEMP_WINTER_MEAN
        seasonal_variation = 5.0   # Less variable in winter
    
    # Fine seasonal adjustment
    seasonal_adjustment = 5.0 * np.sin(2 * np.pi * (day_of_year - 80) / 365.25)
    
    # Diurnal variation (less pronounced than temperate regions)
    diurnal_variation = (TEMP_DAILY_RANGE / 2) * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
    
    # Random variation
    random_variation = rng.normal(0, seasonal_variation)
    
    temperature = seasonal_temp + seasonal_adjustment + diurnal_variation + random_variation
    
    return temperature

def _antarctic_wind(
    day_of_year: int,
    hour_of_day: int,
    weather_pattern: str,
    rng: np.random.Generator
) -> Tuple[float, float]:
    """Generate wind speed and direction."""
    # Base wind speed
    base_speed = WIND_SPEED_MEAN
    
    # Seasonal variation (stronger in winter)
    if day_of_year <= 59 or day_of_year >= 274:  # Summer
        seasonal_factor = 0.8
    else:  # Winter
        seasonal_factor = 1.3
    
    # Weather pattern influence
    pattern_factors = {
        "CLEAR": 0.7,
        "PARTLY_CLOUDY": 0.9,
        "OVERCAST": 1.1,
        "LIGHT_SNOW": 1.2,
        "HEAVY_SNOW": 1.5,
        "BLIZZARD": 2.5,
        "FOG": 0.5,
        "STORM": 3.0,
    }
    pattern_factor = pattern_factors.get(weather_pattern, 1.0)
    
    # Random variation
    wind_speed = base_speed * seasonal_factor * pattern_factor
    wind_speed += rng.normal(0, wind_speed * 0.2)
    wind_speed = max(0.0, wind_speed)
    
    # Wind direction (prevailing westerly with variation)
    if weather_pattern in ["STORM", "BLIZZARD"]:
        # Storm winds more variable
        direction_variation = 90
    else:
        direction_variation = 45
    
    wind_direction = WIND_DIRECTION_BIAS + rng.normal(0, direction_variation)
    wind_direction = wind_direction % 360
    
    return wind_speed, wind_direction

def _classify_weather_pattern(
    temperature: float,
    wind_speed: float,
    humidity: float,
    visibility: float,
    rng: np.random.Generator
) -> str:
    """Classify weather pattern based on environmental conditions."""
    # Blizzard conditions
    if wind_speed > 20.0 and visibility < 500 and temperature < -15.0:
        return "BLIZZARD"
    
    # Storm conditions
    if wind_speed > WIND_SPEED_STORM:
        return "STORM"
    
    # Snow conditions
    if humidity > 85.0 and temperature > -20.0:
        if wind_speed > 10.0:
            return "HEAVY_SNOW"
        else:
            return "LIGHT_SNOW"
    
    # Fog conditions
    if visibility < 1000 and humidity > 90.0 and wind_speed < 5.0:
        return "FOG"
    
    # Clear/cloudy conditions
    if humidity < 70.0 and visibility > 5000:
        return "CLEAR"
    elif humidity < 80.0:
        return "PARTLY_CLOUDY"
    else:
        return "OVERCAST"

def _calculate_visibility(
    weather_pattern: str,
    wind_speed: float,
    humidity: float,
    rng: np.random.Generator
) -> float:
    """Calculate visibility based on weather conditions."""
    base_visibility = {
        "CLEAR": VISIBILITY_GOOD,
        "PARTLY_CLOUDY": 8000,
        "OVERCAST": 5000,
        "LIGHT_SNOW": 2000,
        "HEAVY_SNOW": 500,
        "BLIZZARD": 50,
        "FOG": 200,
        "STORM": 1000,
    }
    
    visibility = base_visibility.get(weather_pattern, 5000)
    
    # Wind can improve or worsen visibility
    if weather_pattern in ["FOG"]:
        # Wind clears fog
        visibility *= (1.0 + wind_speed / 20.0)
    elif weather_pattern in ["HEAVY_SNOW", "BLIZZARD"]:
        # Wind makes snow worse
        visibility *= max(0.1, 1.0 - wind_speed / 50.0)
    
    # Random variation
    visibility *= rng.uniform(0.5, 1.5)
    
    return max(10, visibility)  # Minimum visibility

def _environmental_alerts(
    temperature: float,
    wind_speed: float,
    visibility: float,
    weather_pattern: str,
) -> List[str]:
    """Generate environmental alerts based on conditions."""
    alerts = []
    
    # Temperature alerts
    if temperature < -40.0:
        alerts.append("EXTREME_COLD_WARNING")
    elif temperature < -30.0:
        alerts.append("SEVERE_COLD_WARNING")
    elif temperature > 5.0:
        alerts.append("UNUSUAL_WARMTH_ALERT")
    
    # Wind alerts
    if wind_speed > 50.0:
        alerts.append("EXTREME_WIND_WARNING")
    elif wind_speed > 30.0:
        alerts.append("HIGH_WIND_WARNING")
    
    # Visibility alerts
    if visibility < 100:
        alerts.append("ZERO_VISIBILITY_WARNING")
    elif visibility < 500:
        alerts.append("LOW_VISIBILITY_WARNING")
    
    # Pattern-specific alerts
    if weather_pattern == "BLIZZARD":
        alerts.append("BLIZZARD_WARNING")
    elif weather_pattern == "STORM":
        alerts.append("STORM_WARNING")
    
    return alerts

def generate_environmental_timeseries(
    days: int = DEFAULT_DAYS,
    timesteps_per_day: int = DEFAULT_TIMESTEPS_PER_DAY,
    start_date: Optional[datetime] = None,
    noise_std: float = DEFAULT_NOISE_STD,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate synthetic environmental monitoring time series data.
    
    Returns DataFrame with columns:
    - timestamp: DateTime index
    - air_temperature: Air temperature (°C)
    - ground_temperature: Ground temperature (°C)
    - equipment_temperature: Equipment temperature (°C)
    - wind_speed: Wind speed (m/s)
    - wind_direction: Wind direction (degrees)
    - humidity: Relative humidity (%)
    - pressure: Barometric pressure (hPa)
    - visibility: Visibility distance (meters)
    - snow_accumulation: Snow depth (cm)
    - weather_pattern: Classified weather pattern
    - alert_count: Number of active alerts
    - alerts: List of active alert codes
    - comfort_index: Human comfort index (0-100)
    - equipment_stress: Equipment stress level (0-1)
    """
    if start_date is None:
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    rng = np.random.Generator(np.random.PCG64(seed))
    
    total_timesteps = days * timesteps_per_day
    dt_hours = 24.0 / timesteps_per_day
    
    log.info(
        "environmental_synthetic.generating_timeseries",
        days=days,
        timesteps_per_day=timesteps_per_day,
        total_timesteps=total_timesteps,
        dt_hours=dt_hours,
    )
    
    # Initialize arrays
    timestamps = []
    air_temperature = np.zeros(total_timesteps)
    ground_temperature = np.zeros(total_timesteps)
    equipment_temperature = np.zeros(total_timesteps)
    wind_speed = np.zeros(total_timesteps)
    wind_direction = np.zeros(total_timesteps)
    humidity = np.zeros(total_timesteps)
    pressure = np.zeros(total_timesteps)
    visibility = np.zeros(total_timesteps)
    snow_accumulation = np.zeros(total_timesteps)
    weather_patterns = []
    alert_counts = np.zeros(total_timesteps, dtype=int)
    all_alerts = []
    comfort_index = np.zeros(total_timesteps)
    equipment_stress = np.zeros(total_timesteps)
    
    # Initialize state
    current_snow = 0.0  # Starting snow depth
    
    for i in range(total_timesteps):
        current_time = start_date + timedelta(hours=i * dt_hours)
        timestamps.append(current_time)
        
        day_of_year = current_time.timetuple().tm_yday
        hour_of_day = current_time.hour
        
        # Generate base environmental conditions
        air_temp = _antarctic_temperature(day_of_year, hour_of_day, rng)
        
        # Ground temperature (lags air temperature, insulated by snow)
        ground_temp = air_temp * 0.7 + (current_snow / 100.0) * 5.0  # Snow insulation
        
        # Equipment temperature (heated, but affected by extreme conditions)
        if air_temp < -30.0:
            equip_temp = max(-10.0, air_temp + 25.0)  # Heating struggles
        else:
            equip_temp = max(5.0, air_temp + 30.0)  # Normal heating
        
        # Humidity (higher when warmer, lower when very cold)
        if air_temp > -10.0:
            base_humidity = HUMIDITY_BASE + (air_temp + 10.0) * 2.0
        else:
            base_humidity = HUMIDITY_BASE - (abs(air_temp) - 10.0) * 1.5
        humid = max(20.0, min(100.0, base_humidity + rng.normal(0, 10)))
        
        # Pressure (varies with weather systems)
        press = PRESSURE_BASE + rng.normal(0, 15) + 5.0 * np.sin(2 * np.pi * day_of_year / 30)
        
        # Preliminary weather pattern (will be refined)
        temp_weather = rng.choice(WEATHER_PATTERNS, p=[0.2, 0.2, 0.15, 0.15, 0.1, 0.05, 0.1, 0.05])
        
        # Wind based on preliminary weather
        ws, wd = _antarctic_wind(day_of_year, hour_of_day, temp_weather, rng)
        
        # Visibility
        vis = _calculate_visibility(temp_weather, ws, humid, rng)
        
        # Final weather pattern classification
        weather_pattern = _classify_weather_pattern(air_temp, ws, humid, vis, rng)
        
        # Snow accumulation
        if weather_pattern in ["LIGHT_SNOW", "HEAVY_SNOW", "BLIZZARD"]:
            if weather_pattern == "LIGHT_SNOW":
                snow_rate = 0.5  # cm/hour
            elif weather_pattern == "HEAVY_SNOW":
                snow_rate = 2.0
            else:  # BLIZZARD
                snow_rate = 5.0
            current_snow += snow_rate * dt_hours
        
        # Snow sublimation/melting
        if air_temp > 0.0:
            melt_rate = air_temp * 0.5 * dt_hours
            current_snow = max(0.0, current_snow - melt_rate)
        elif ws > 15.0:  # Wind sublimation
            sublimation_rate = (ws - 15.0) * 0.1 * dt_hours
            current_snow = max(0.0, current_snow - sublimation_rate)
        
        # Environmental alerts
        alerts = _environmental_alerts(air_temp, ws, vis, weather_pattern)
        
        # Comfort index (0-100, higher is more comfortable)
        comfort = 50.0  # Baseline
        
        # Temperature comfort
        if -5.0 <= air_temp <= 0.0:
            comfort += 20.0  # Optimal range
        else:
            comfort -= abs(air_temp + 2.5) * 2.0  # Penalty for deviation
        
        # Wind comfort
        if ws < 10.0:
            comfort += 10.0
        else:
            comfort -= (ws - 10.0) * 2.0
        
        # Visibility comfort
        if vis > 5000:
            comfort += 10.0
        else:
            comfort -= (5000 - vis) / 100.0
        
        comfort = max(0.0, min(100.0, comfort))
        
        # Equipment stress (0-1, higher is more stress)
        stress = 0.0
        
        # Temperature stress
        if air_temp < -30.0:
            stress += (abs(air_temp) - 30.0) / 50.0
        elif air_temp > 5.0:
            stress += (air_temp - 5.0) / 20.0
        
        # Wind stress
        if ws > 25.0:
            stress += (ws - 25.0) / 50.0
        
        # Humidity stress (both too high and too low)
        if humid > 90.0:
            stress += (humid - 90.0) / 20.0
        elif humid < 30.0:
            stress += (30.0 - humid) / 30.0
        
        stress = min(1.0, stress)
        
        # Store values
        air_temperature[i] = air_temp
        ground_temperature[i] = ground_temp
        equipment_temperature[i] = equip_temp
        wind_speed[i] = ws
        wind_direction[i] = wd
        humidity[i] = humid
        pressure[i] = press
        visibility[i] = vis
        snow_accumulation[i] = current_snow
        weather_patterns.append(weather_pattern)
        alert_counts[i] = len(alerts)
        all_alerts.append(alerts)
        comfort_index[i] = comfort
        equipment_stress[i] = stress
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'air_temperature': air_temperature,
        'ground_temperature': ground_temperature,
        'equipment_temperature': equipment_temperature,
        'wind_speed': wind_speed,
        'wind_direction': wind_direction,
        'humidity': humidity,
        'pressure': pressure,
        'visibility': visibility,
        'snow_accumulation': snow_accumulation,
        'weather_pattern': weather_patterns,
        'alert_count': alert_counts,
        'alerts': all_alerts,
        'comfort_index': comfort_index,
        'equipment_stress': equipment_stress,
    })
    
    # Add noise to sensor readings
    noise_cols = ['air_temperature', 'ground_temperature', 'wind_speed', 'humidity', 'pressure']
    for col in noise_cols:
        noise = rng.normal(0, df[col].std() * noise_std, len(df))
        df[col] = df[col] + noise
    
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
        "environmental_synthetic.generating_split",
        total_days=days,
        train_days=train_days,
        val_days=val_days,
    )
    
    # Generate training data
    df_train = generate_environmental_timeseries(
        days=train_days,
        seed=seed,
    )
    
    # Generate validation data
    val_start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=train_days)
    df_val = generate_environmental_timeseries(
        days=val_days,
        start_date=val_start,
        seed=seed + 2000 if seed is not None else None,
    )
    
    return df_train, df_val

def describe_environmental_data(df: pd.DataFrame, name: str = "environmental_data") -> None:
    """Print descriptive statistics for environmental dataset."""
    print(f"\n=== {name.upper()} DATASET SUMMARY ===")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Total timesteps: {len(df)}")
    print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    
    print(f"\nTEMPERATURE:")
    print(f"  Air: {df['air_temperature'].mean():.1f} ± {df['air_temperature'].std():.1f}°C (range: {df['air_temperature'].min():.1f} to {df['air_temperature'].max():.1f}°C)")
    print(f"  Ground: {df['ground_temperature'].mean():.1f} ± {df['ground_temperature'].std():.1f}°C")
    print(f"  Equipment: {df['equipment_temperature'].mean():.1f} ± {df['equipment_temperature'].std():.1f}°C")
    
    print(f"\nWIND:")
    print(f"  Speed: {df['wind_speed'].mean():.1f} ± {df['wind_speed'].std():.1f} m/s (max: {df['wind_speed'].max():.1f} m/s)")
    print(f"  High wind events (>25 m/s): {(df['wind_speed'] > 25).sum()} / {len(df)}")
    
    print(f"\nOTHER CONDITIONS:")
    print(f"  Humidity: {df['humidity'].mean():.1f} ± {df['humidity'].std():.1f}%")
    print(f"  Pressure: {df['pressure'].mean():.1f} ± {df['pressure'].std():.1f} hPa")
    print(f"  Visibility: {df['visibility'].mean():.0f} ± {df['visibility'].std():.0f} m")
    print(f"  Snow depth: {df['snow_accumulation'].mean():.1f} ± {df['snow_accumulation'].std():.1f} cm (max: {df['snow_accumulation'].max():.1f} cm)")
    
    print(f"\nWEATHER PATTERNS:")
    pattern_counts = df['weather_pattern'].value_counts()
    for pattern, count in pattern_counts.items():
        print(f"  {pattern}: {count} ({count/len(df)*100:.1f}%)")
    
    print(f"\nALERTS & INDICES:")
    print(f"  Total alerts: {df['alert_count'].sum()}")
    print(f"  Alert rate: {(df['alert_count'] > 0).sum() / len(df) * 100:.1f}% of time")
    print(f"  Average comfort index: {df['comfort_index'].mean():.1f} ± {df['comfort_index'].std():.1f}")
    print(f"  Average equipment stress: {df['equipment_stress'].mean():.3f} ± {df['equipment_stress'].std():.3f}")
    
    print("="*50)

if __name__ == "__main__":
    # Generate sample data for testing
    df_train, df_val = generate_train_val_split(days=90, seed=42)
    
    describe_environmental_data(df_train, "Training")
    describe_environmental_data(df_val, "Validation")