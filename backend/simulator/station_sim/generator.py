"""Sensor data generator for the VajraX station simulator.

Reads the current StationState and produces SensorReading-compatible dicts
for every sensor defined in the station config YAML.

The generator is stateless itself — all state lives in StationState.
It maps from sensor_id → state field using a dispatch table populated
at construction time from the station config.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from shared.schemas.config import SensorConfig, StationConfig
from shared.utils.time import utcnow
from simulator.station_sim.state import StationState


# ---------------------------------------------------------------------------
# Reading schema (proto-compatible dict — converted to Protobuf in Phase 3)
# ---------------------------------------------------------------------------

def make_reading(
    station_id: str,
    sensor_id: str,
    domain: str,
    metric_name: str,
    value: float,
    unit: str,
    asset_id: Optional[str],
    quality: str = "NOMINAL",
    timestamp_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return a SensorReading-compatible dict."""
    return {
        "station_id": station_id,
        "sensor_id": sensor_id,
        "domain": domain,
        "metric_name": metric_name,
        "value": round(value, 4),
        "unit": unit,
        "quality": quality,
        "asset_id": asset_id or "",
        "timestamp_utc": (timestamp_utc or utcnow()).isoformat(),
        "is_aggregate": False,
        "aggregation_window_s": 0,
    }


def make_batch(
    station_id: str,
    readings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Wrap readings in a SensorBatch-compatible dict."""
    return {
        "station_id": station_id,
        "readings": readings,
        "batch_id": str(uuid.uuid4()),
        "generated_at": utcnow().isoformat(),
        "sequence_number": 0,  # sync agent assigns real sequence numbers in Phase 3
        "is_aggregate": False,
        "aggregation_window_s": 0,
    }


# ---------------------------------------------------------------------------
# Value extractor dispatch table
# Each entry maps a metric_name → a callable(state) -> float
# ---------------------------------------------------------------------------

def _build_extractor_table(station_id: str) -> Dict[str, Callable[[StationState], float]]:
    """Build a dispatch table from metric_name → state extractor function."""
    return {
        # Generator 1
        "fuel_level_percent":           lambda s: s.gen1.fuel_pct,
        "power_output_kw":              lambda s: s.gen1.power_output_kw,
        "fuel_consumption_lph":         lambda s: s.gen1.fuel_consumption_lph,
        "oil_pressure_bar":             lambda s: s.gen1.oil_pressure_bar,
        "coolant_temp_c":               lambda s: s.gen1.coolant_temp_c,
        "generator_status":             lambda s: s.gen1.status,
        # Grid
        "total_load_kw":                lambda s: s.grid.total_load_kw,
        "solar_output_kw":              lambda s: s.grid.solar_output_kw,
        "solar_irradiance_wm2":         lambda s: s.weather.solar_irradiance_wm2,
        # Weather
        "ambient_temp_c":               lambda s: s.weather.ambient_temp_c,
        "wind_speed_ms":                lambda s: s.weather.wind_speed_ms,
        "wind_direction_deg":           lambda s: s.weather.wind_direction_deg,
        "pressure_hpa":                 lambda s: s.weather.pressure_hpa,
        "relative_humidity_pct":        lambda s: s.weather.humidity_pct,
        "visibility_km":                lambda s: s.weather.visibility_km,
        "uv_index":                     lambda s: s.weather.uv_index,
        # Environment — air quality
        "co2_ppm":                      lambda s: s.environment.co2_ppm,
        "co_ppm":                       lambda s: s.environment.co_ppm,
        "pm25_ugm3":                    lambda s: s.environment.pm25_ugm3,
        # Environment — fire detection (zone dispatch by sensor_id)
        "fire_state":                   _fire_extractor,
        # Environment — seismic
        "seismic_magnitude":            lambda s: s.environment.seismic_magnitude,
        # Environment — ice (Bharati)
        "ice_thickness_cm":             lambda s: s.environment.ice_thickness_cm,
    }


def _fire_extractor(state: StationState) -> float:
    """Called by the dispatch table — returns placeholder (see _get_value for special casing)."""
    return 0.0  # overridden in SensorDataGenerator._get_value


class SensorDataGenerator:
    """Generates sensor readings from StationState for all configured sensors."""

    def __init__(self, config: StationConfig, state: StationState) -> None:
        self.config = config
        self.state = state
        self._extractors = _build_extractor_table(config.station_id.value)

    def generate_all(self) -> List[Dict[str, Any]]:
        """Generate one reading per configured sensor at the current state.

        Returns:
            List of SensorReading-compatible dicts, one per sensor.
        """
        now = utcnow()
        readings = []
        for sensor in self.config.sensors:
            value = self._get_value(sensor)
            quality = self._assess_quality(sensor, value)
            readings.append(make_reading(
                station_id=self.config.station_id.value,
                sensor_id=sensor.sensor_id,
                domain=sensor.domain.value,
                metric_name=sensor.metric_name,
                value=value,
                unit=sensor.unit,
                asset_id=sensor.asset_id,
                quality=quality,
                timestamp_utc=now,
            ))
        return readings

    def generate_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Generate readings only for sensors in the specified domain."""
        now = utcnow()
        readings = []
        for sensor in self.config.sensors:
            if sensor.domain.value != domain:
                continue
            value = self._get_value(sensor)
            quality = self._assess_quality(sensor, value)
            readings.append(make_reading(
                station_id=self.config.station_id.value,
                sensor_id=sensor.sensor_id,
                domain=sensor.domain.value,
                metric_name=sensor.metric_name,
                value=value,
                unit=sensor.unit,
                asset_id=sensor.asset_id,
                quality=quality,
                timestamp_utc=now,
            ))
        return readings

    def _get_value(self, sensor: SensorConfig) -> float:
        """Extract the current value for a sensor from state."""
        metric = sensor.metric_name

        # Special case: fire_state dispatch by zone suffix in sensor_id
        if metric == "fire_state":
            sid = sensor.sensor_id
            if "fire_z1" in sid:
                return self.state.environment.fire_z1
            elif "fire_z2" in sid:
                return self.state.environment.fire_z2
            elif "fire_z3" in sid:
                return self.state.environment.fire_z3
            return 0.0

        extractor = self._extractors.get(metric)
        if extractor is None:
            return 0.0
        return extractor(self.state)

    def _assess_quality(self, sensor: SensorConfig, value: float) -> str:
        """Determine quality flag for a reading."""
        # Out-of-range values are flagged as DEGRADED
        if sensor.nominal_min is not None and value < sensor.nominal_min * 0.95:
            return "DEGRADED"
        if sensor.nominal_max is not None and value > sensor.nominal_max * 1.05:
            return "DEGRADED"
        return "NOMINAL"
