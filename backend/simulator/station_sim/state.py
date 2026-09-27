"""Station state machine for the VajraX sensor simulator.

Maintains a mutable physical model of each station's current state.
The generator reads from this state to produce sensor readings.
The anomaly injector modifies this state to simulate failures.

Design principles:
- Every sensor has a current value, noise parameters, and drift direction.
- State is advanced in discrete time steps (one step = one sampling tick).
- Active anomalies are stored as a dict keyed by anomaly name; they
  override normal physics while active.
- Thread-safe: all mutations go through methods protected by asyncio.Lock.
"""
from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class AnomalyType(str, Enum):
    """Named anomaly scenarios injectable into the station simulator."""
    GENERATOR_FAULT = "generator_fault"         # gen1 output drops to 0, status=FAULT
    FUEL_DRAIN = "fuel_drain"                   # fuel consumption 10× normal rate
    FIRE_ZONE_1 = "fire_zone_1"                 # fire sensor zone 1 ACTIVE
    FIRE_ZONE_2 = "fire_zone_2"                 # fire sensor zone 2 ACTIVE
    FIRE_ZONE_3 = "fire_zone_3"                 # fire sensor zone 3 ACTIVE (Maitri only)
    SEISMIC_MEDIUM = "seismic_medium"           # one-shot M3.5 seismic event
    SEISMIC_HIGH = "seismic_high"               # one-shot M5.0 seismic event
    SEISMIC_CRITICAL = "seismic_critical"       # one-shot M6.5 seismic event
    CO_LEAK = "co_leak"                         # CO concentration rising above PEL
    HVAC_FAILURE = "hvac_failure"               # indoor temperature rising
    SENSOR_DROPOUT = "sensor_dropout"           # a sensor stops reporting (staleness)
    WIND_STORM = "wind_storm"                   # extreme wind speed
    ICE_THINNING = "ice_thinning"               # Bharati-specific: ice thickness dropping


@dataclass
class GeneratorState:
    """Physical state of a single diesel generator."""
    fuel_pct: float = 85.0          # percent full (0–100)
    power_output_kw: float = 80.0   # current output in kW
    fuel_consumption_lph: float = 15.0  # litres per hour at current load
    oil_pressure_bar: float = 4.5
    coolant_temp_c: float = 85.0
    engine_rpm: float = 1500.0
    status: float = 1.0             # 0=OFF, 1=RUNNING, 2=FAULT

    # Simulation parameters (not sensor values)
    nominal_consumption_lph: float = 15.0
    tank_capacity_litres: float = 5000.0


@dataclass
class WeatherState:
    """Current weather conditions at a station."""
    ambient_temp_c: float = -35.0
    wind_speed_ms: float = 8.0
    wind_direction_deg: float = 225.0
    pressure_hpa: float = 985.0
    humidity_pct: float = 65.0
    visibility_km: float = 10.0
    uv_index: float = 0.0           # solar UV (Bharati only)
    solar_irradiance_wm2: float = 0.0  # solar irradiance (Bharati only)

    # Simulation time offset (simulated hours since midnight)
    sim_hour: float = 0.0


@dataclass
class EnvironmentState:
    """Air quality, fire detection, seismic, and ice monitoring state."""
    co2_ppm: float = 450.0
    co_ppm: float = 3.0
    pm25_ugm3: float = 5.0
    fire_z1: float = 0.0            # 0=CLEAR, 1=ACTIVE, 2=FAULT
    fire_z2: float = 0.0
    fire_z3: float = 0.0            # Maitri zone 3 (generator room)
    seismic_magnitude: float = 0.0  # 0.0 between events
    ice_thickness_cm: float = 150.0 # Bharati only

    # Seismic event one-shot state
    _seismic_event_ticks_remaining: int = 0


@dataclass
class GridState:
    """Power distribution state."""
    total_load_kw: float = 75.0
    solar_output_kw: float = 0.0    # Bharati only


@dataclass
class StationState:
    """Complete mutable physical state of a simulated station.

    One instance per station. The simulator generator reads this state
    to produce SensorReading values; the anomaly injector writes to it.
    """
    station_id: str = ""
    gen1: GeneratorState = field(default_factory=GeneratorState)
    gen2: GeneratorState = field(default_factory=lambda: GeneratorState(
        fuel_pct=92.0, status=0.0, power_output_kw=0.0  # backup off by default
    ))
    weather: WeatherState = field(default_factory=WeatherState)
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    grid: GridState = field(default_factory=GridState)

    # Active anomalies: name → metadata dict
    active_anomalies: Dict[str, dict] = field(default_factory=dict)

    # Simulation tick counter (increments on each step)
    tick: int = 0
    # Simulated seconds elapsed since simulator start
    elapsed_s: float = 0.0

    # Placeholder — actual lock is assigned in __post_init__
    _lock_instance: asyncio.Lock | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Do NOT create asyncio.Lock here — it must be created inside a running
        # event loop. The lock is created on first use via get_lock().
        pass

    def get_lock(self) -> asyncio.Lock:
        """Return the asyncio.Lock, creating it lazily on the current event loop."""
        if self._lock_instance is None:
            object.__setattr__(self, "_lock_instance", asyncio.Lock())
        return self._lock_instance

    # Expose as _lock property for backward compatibility with callers
    @property
    def _lock(self) -> asyncio.Lock:
        return self.get_lock()


    @classmethod
    def for_station(cls, station_id: str) -> "StationState":
        """Create a station state with station-specific initial conditions."""
        state = cls(station_id=station_id)
        if station_id == "bharati":
            # Bharati is slightly warmer (coastal, lower elevation)
            state.weather.ambient_temp_c = -20.0
            state.weather.wind_speed_ms = 6.0
            state.weather.pressure_hpa = 995.0
            state.gen1.power_output_kw = 120.0
            state.gen1.fuel_consumption_lph = 22.0
            state.gen1.nominal_consumption_lph = 22.0
            state.gen1.tank_capacity_litres = 8000.0
            state.grid.total_load_kw = 110.0
            state.environment.ice_thickness_cm = 150.0
        return state

    async def step(self, delta_s: float) -> None:
        """Advance simulation by delta_s seconds (called by background task)."""
        async with self._lock:
            self.tick += 1
            self.elapsed_s += delta_s
            self._step_weather(delta_s)
            self._step_generators(delta_s)
            self._step_environment(delta_s)
            self._step_anomalies(delta_s)

    def _step_weather(self, delta_s: float) -> None:
        """Advance weather state with realistic variation."""
        w = self.weather
        # Simulated time of day (cycles every 24h of sim time)
        w.sim_hour = (w.sim_hour + delta_s / 3600.0) % 24.0
        hour_rad = 2 * math.pi * w.sim_hour / 24.0

        # Temperature: daily cycle ±5°C + slow noise
        base_temp = -35.0 if self.station_id == "maitri" else -20.0
        w.ambient_temp_c = base_temp + 5.0 * math.sin(hour_rad) + _noise(0.3)

        # Wind: mean + gusts modelled as slow random walk
        w.wind_speed_ms = max(0.0, w.wind_speed_ms + _noise(0.5) - 0.02)
        w.wind_speed_ms = min(w.wind_speed_ms, 25.0)  # cap at pre-storm unless anomaly

        # Wind direction: slow drift
        w.wind_direction_deg = (w.wind_direction_deg + _noise(2.0)) % 360.0

        # Pressure: slow variation
        w.pressure_hpa += _noise(0.1)
        w.pressure_hpa = max(960.0, min(1040.0, w.pressure_hpa))

        # Humidity
        w.humidity_pct += _noise(0.2)
        w.humidity_pct = max(20.0, min(100.0, w.humidity_pct))

        # UV and solar (Bharati only): sinusoidal with polar day/night
        if self.station_id == "bharati":
            solar_factor = max(0.0, math.sin(hour_rad))
            w.solar_irradiance_wm2 = 400.0 * solar_factor + _noise(10.0)
            w.uv_index = 3.0 * solar_factor + _noise(0.1)
            w.solar_irradiance_wm2 = max(0.0, w.solar_irradiance_wm2)
            w.uv_index = max(0.0, w.uv_index)

    def _step_generators(self, delta_s: float) -> None:
        """Advance generator state: fuel burn, output variation."""
        g = self.gen1
        if g.status == 1.0:  # RUNNING
            # Fuel decreases: consumption rate converts L/hr → pct/s
            pct_per_second = (g.fuel_consumption_lph / 3600.0) / g.tank_capacity_litres * 100.0
            g.fuel_pct = max(0.0, g.fuel_pct - pct_per_second * delta_s)
            # Power output: nominal load ± small fluctuations
            g.power_output_kw = max(0.0, self.grid.total_load_kw + _noise(2.0))
            # Oil pressure: stable with minor noise
            g.oil_pressure_bar = 4.5 + _noise(0.05)
            g.coolant_temp_c = 85.0 + _noise(0.5)
            # Fuel consumption rate with slight load-based variation
            g.fuel_consumption_lph = g.nominal_consumption_lph * (
                g.power_output_kw / 80.0
            ) + _noise(0.3)
            g.fuel_consumption_lph = max(0.0, g.fuel_consumption_lph)
        else:
            g.power_output_kw = 0.0
            g.fuel_consumption_lph = 0.0

        # Grid load: slow variation
        self.grid.total_load_kw = max(20.0, self.grid.total_load_kw + _noise(1.0))

        # Solar output (Bharati only)
        if self.station_id == "bharati":
            self.grid.solar_output_kw = max(0.0, self.weather.solar_irradiance_wm2 * 0.12)

    def _step_environment(self, delta_s: float) -> None:
        """Advance air quality and ice state."""
        e = self.environment
        # CO2: slow drift around nominal indoor level
        e.co2_ppm += _noise(1.0)
        e.co2_ppm = max(350.0, min(1000.0, e.co2_ppm))
        # CO: very slow background level
        e.co_ppm += _noise(0.05)
        e.co_ppm = max(0.0, min(10.0, e.co_ppm))
        # PM2.5: slow variation
        e.pm25_ugm3 += _noise(0.1)
        e.pm25_ugm3 = max(0.0, min(25.0, e.pm25_ugm3))
        # Seismic: decay one-shot event back to 0
        if e._seismic_event_ticks_remaining > 0:
            e._seismic_event_ticks_remaining -= 1
        else:
            e.seismic_magnitude = 0.0
        # Ice thickness (Bharati): very slow seasonal change
        if self.station_id == "bharati":
            e.ice_thickness_cm += _noise(0.001)
            e.ice_thickness_cm = max(0.0, min(300.0, e.ice_thickness_cm))

    def _step_anomalies(self, delta_s: float) -> None:
        """Apply active anomaly overrides to state."""
        if AnomalyType.GENERATOR_FAULT in self.active_anomalies:
            self.gen1.status = 2.0
            self.gen1.power_output_kw = 0.0
            self.gen1.fuel_consumption_lph = 0.0

        if AnomalyType.FUEL_DRAIN in self.active_anomalies:
            # 10× normal consumption rate
            pct_per_second = (self.gen1.nominal_consumption_lph * 10.0 / 3600.0) / \
                             self.gen1.tank_capacity_litres * 100.0
            self.gen1.fuel_pct = max(0.0, self.gen1.fuel_pct - pct_per_second * delta_s)
            self.gen1.fuel_consumption_lph = self.gen1.nominal_consumption_lph * 10.0

        if AnomalyType.FIRE_ZONE_1 in self.active_anomalies:
            self.environment.fire_z1 = 1.0
        if AnomalyType.FIRE_ZONE_2 in self.active_anomalies:
            self.environment.fire_z2 = 1.0
        if AnomalyType.FIRE_ZONE_3 in self.active_anomalies:
            self.environment.fire_z3 = 1.0

        if AnomalyType.CO_LEAK in self.active_anomalies:
            self.environment.co_ppm = min(150.0, self.environment.co_ppm + 0.5 * delta_s)

        if AnomalyType.HVAC_FAILURE in self.active_anomalies:
            # Indoor temp sensor would be on a separate asset; we model via CO2 proxy
            self.environment.co2_ppm = min(2000.0, self.environment.co2_ppm + 1.0 * delta_s)

        if AnomalyType.WIND_STORM in self.active_anomalies:
            self.weather.wind_speed_ms = min(65.0, self.weather.wind_speed_ms + 0.5 * delta_s)

        if AnomalyType.ICE_THINNING in self.active_anomalies and self.station_id == "bharati":
            self.environment.ice_thickness_cm = max(
                0.0, self.environment.ice_thickness_cm - 0.05 * delta_s
            )

    def inject_anomaly(self, anomaly: AnomalyType, meta: Optional[dict] = None) -> None:
        """Activate an anomaly. One-shot seismic events are handled specially."""
        meta = meta or {}
        if anomaly == AnomalyType.SEISMIC_MEDIUM:
            self.environment.seismic_magnitude = 3.5 + random.uniform(0, 0.9)
            self.environment._seismic_event_ticks_remaining = 10
        elif anomaly == AnomalyType.SEISMIC_HIGH:
            self.environment.seismic_magnitude = 5.0 + random.uniform(0, 1.4)
            self.environment._seismic_event_ticks_remaining = 15
        elif anomaly == AnomalyType.SEISMIC_CRITICAL:
            self.environment.seismic_magnitude = 6.5 + random.uniform(0, 1.0)
            self.environment._seismic_event_ticks_remaining = 30
        else:
            self.active_anomalies[anomaly] = meta

    def clear_anomaly(self, anomaly: AnomalyType) -> bool:
        """Deactivate an anomaly. Returns True if it was active."""
        if anomaly in self.active_anomalies:
            del self.active_anomalies[anomaly]
            # Restore relevant state
            if anomaly == AnomalyType.GENERATOR_FAULT:
                self.gen1.status = 1.0
            if anomaly == AnomalyType.FIRE_ZONE_1:
                self.environment.fire_z1 = 0.0
            if anomaly == AnomalyType.FIRE_ZONE_2:
                self.environment.fire_z2 = 0.0
            if anomaly == AnomalyType.FIRE_ZONE_3:
                self.environment.fire_z3 = 0.0
            return True
        return False

    def clear_all_anomalies(self) -> None:
        """Clear all active anomalies and restore normal state."""
        for anomaly in list(self.active_anomalies.keys()):
            self.clear_anomaly(anomaly)

    def snapshot(self) -> dict:
        """Return a JSON-serializable snapshot of current state."""
        return {
            "station_id": self.station_id,
            "tick": self.tick,
            "elapsed_s": self.elapsed_s,
            "active_anomalies": list(self.active_anomalies.keys()),
            "gen1_fuel_pct": round(self.gen1.fuel_pct, 2),
            "gen1_status": self.gen1.status,
            "gen1_power_kw": round(self.gen1.power_output_kw, 1),
            "ambient_temp_c": round(self.weather.ambient_temp_c, 1),
            "wind_speed_ms": round(self.weather.wind_speed_ms, 1),
            "co_ppm": round(self.environment.co_ppm, 1),
            "fire_z1": self.environment.fire_z1,
            "fire_z2": self.environment.fire_z2,
            "seismic_mag": self.environment.seismic_magnitude,
        }


def _noise(scale: float) -> float:
    """Return Gaussian noise with the given standard deviation."""
    return random.gauss(0.0, scale)
