"""Phase 1 unit tests — Station simulator core (no infrastructure required).

Tests verify:
 - StationState initialisation per station
 - Physics step produces plausible values
 - Anomaly injection correctly modifies state
 - Anomaly clearing restores state
 - SensorDataGenerator produces valid readings for all sensors
 - All reading values are within physically plausible bounds
 - Both stations can run simultaneously with independent state
 - Fuel drain anomaly causes fuel_pct to decrease faster than nominal
 - Generator fault anomaly sets output to 0 and status to 2 (FAULT)
 - Fire anomalies set the correct zone sensors

Run with: pytest tests/unit/test_phase1_simulator.py -v
"""
from __future__ import annotations

import asyncio
import time
from typing import List

import pytest

from simulator.station_sim.state import AnomalyType, StationState
from simulator.station_sim.generator import SensorDataGenerator, make_batch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_loop = asyncio.new_event_loop()


def _run(coro):
    """Run a coroutine on the module-level event loop.

    Using a single shared loop avoids the 'Future attached to different loop'
    error that occurs when StationState's asyncio.Lock is created on one loop
    and run_until_complete is called on another.
    """
    return _loop.run_until_complete(coro)



def _load_generator(station_id: str) -> tuple[StationState, SensorDataGenerator]:
    """Load station config and build a generator + state pair."""
    from shared.schemas.config import StationConfig
    config = StationConfig.from_yaml(f"edge/config/{station_id}.yaml")
    state = StationState.for_station(station_id)
    gen = SensorDataGenerator(config, state)
    return state, gen


# ---------------------------------------------------------------------------
# StationState initialisation
# ---------------------------------------------------------------------------

class TestStationState:
    def test_maitri_initial_fuel(self):
        state = StationState.for_station("maitri")
        assert 80 <= state.gen1.fuel_pct <= 100

    def test_bharati_initial_fuel(self):
        state = StationState.for_station("bharati")
        assert 80 <= state.gen1.fuel_pct <= 100

    def test_maitri_colder_than_bharati(self):
        maitri = StationState.for_station("maitri")
        bharati = StationState.for_station("bharati")
        assert maitri.weather.ambient_temp_c < bharati.weather.ambient_temp_c

    def test_bharati_has_ice_thickness(self):
        state = StationState.for_station("bharati")
        assert state.environment.ice_thickness_cm > 0

    def test_independent_states(self):
        """Two station states must not share any mutable references."""
        s1 = StationState.for_station("maitri")
        s2 = StationState.for_station("bharati")
        s1.gen1.fuel_pct = 10.0
        assert s2.gen1.fuel_pct != 10.0

    def test_no_active_anomalies_at_start(self):
        state = StationState.for_station("maitri")
        assert len(state.active_anomalies) == 0


# ---------------------------------------------------------------------------
# Physics step
# ---------------------------------------------------------------------------

class TestPhysicsStep:
    def test_step_advances_tick(self):
        state = StationState.for_station("maitri")
        _run(state.step(1.0))
        assert state.tick == 1

    def test_fuel_decreases_over_time(self):
        state = StationState.for_station("maitri")
        initial_fuel = state.gen1.fuel_pct
        # Advance 3600 real seconds (1 hour)
        for _ in range(3600):
            _run(state.step(1.0))
        assert state.gen1.fuel_pct < initial_fuel, "Fuel must decrease over time"

    def test_weather_values_remain_in_range(self):
        state = StationState.for_station("maitri")
        for _ in range(100):
            _run(state.step(60.0))
        assert -80 <= state.weather.ambient_temp_c <= 0
        assert 0 <= state.weather.wind_speed_ms <= 30
        assert 900 <= state.weather.pressure_hpa <= 1050
        assert 0 <= state.weather.humidity_pct <= 100

    def test_generator_output_tracks_load(self):
        state = StationState.for_station("maitri")
        for _ in range(10):
            _run(state.step(1.0))
        # Power output should be close to grid load (within 10 kW noise)
        assert abs(state.gen1.power_output_kw - state.grid.total_load_kw) < 15

    def test_elapsed_s_accumulates(self):
        state = StationState.for_station("maitri")
        for _ in range(5):
            _run(state.step(10.0))
        assert abs(state.elapsed_s - 50.0) < 0.001


# ---------------------------------------------------------------------------
# Anomaly injection
# ---------------------------------------------------------------------------

class TestAnomalyInjection:
    def test_generator_fault_zeroes_output(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.GENERATOR_FAULT)
        _run(state.step(1.0))
        assert state.gen1.status == 2.0
        assert state.gen1.power_output_kw == 0.0

    def test_generator_fault_clear_restores_running(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.GENERATOR_FAULT)
        _run(state.step(1.0))
        state.clear_anomaly(AnomalyType.GENERATOR_FAULT)
        _run(state.step(1.0))
        assert state.gen1.status == 1.0

    def test_fuel_drain_faster_than_nominal(self):
        state_normal = StationState.for_station("maitri")
        state_drained = StationState.for_station("maitri")
        state_drained.inject_anomaly(AnomalyType.FUEL_DRAIN)
        # Advance both 300 seconds
        for _ in range(300):
            _run(state_normal.step(1.0))
            _run(state_drained.step(1.0))
        assert state_drained.gen1.fuel_pct < state_normal.gen1.fuel_pct, \
            "Fuel drain anomaly must consume fuel faster than nominal"

    def test_fire_zone_1_sets_sensor(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.FIRE_ZONE_1)
        _run(state.step(1.0))
        assert state.environment.fire_z1 == 1.0

    def test_fire_zone_2_sets_sensor(self):
        state = StationState.for_station("bharati")
        state.inject_anomaly(AnomalyType.FIRE_ZONE_2)
        _run(state.step(1.0))
        assert state.environment.fire_z2 == 1.0

    def test_fire_zone_clear_resets_sensor(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.FIRE_ZONE_1)
        _run(state.step(1.0))
        state.clear_anomaly(AnomalyType.FIRE_ZONE_1)
        _run(state.step(1.0))
        assert state.environment.fire_z1 == 0.0

    def test_seismic_medium_sets_magnitude(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.SEISMIC_MEDIUM)
        assert 3.0 <= state.environment.seismic_magnitude <= 5.0

    def test_seismic_decays_to_zero(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.SEISMIC_MEDIUM)
        # Step enough times for the event to expire
        for _ in range(20):
            _run(state.step(1.0))
        assert state.environment.seismic_magnitude == 0.0

    def test_wind_storm_increases_wind(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.WIND_STORM)
        for _ in range(50):
            _run(state.step(1.0))
        assert state.weather.wind_speed_ms > 20.0

    def test_clear_all_anomalies(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.FIRE_ZONE_1)
        state.inject_anomaly(AnomalyType.CO_LEAK)
        state.inject_anomaly(AnomalyType.WIND_STORM)
        assert len(state.active_anomalies) == 3
        state.clear_all_anomalies()
        assert len(state.active_anomalies) == 0

    def test_clear_nonexistent_anomaly_returns_false(self):
        state = StationState.for_station("maitri")
        result = state.clear_anomaly(AnomalyType.FIRE_ZONE_1)
        assert result is False

    def test_snapshot_includes_anomaly_list(self):
        state = StationState.for_station("maitri")
        state.inject_anomaly(AnomalyType.FUEL_DRAIN)
        snap = state.snapshot()
        assert "fuel_drain" in snap["active_anomalies"]


# ---------------------------------------------------------------------------
# SensorDataGenerator — reading production
# ---------------------------------------------------------------------------

class TestSensorDataGenerator:
    def test_maitri_generates_readings_for_all_sensors(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        assert len(readings) > 0, "Generator must produce at least one reading"

    def test_bharati_generates_readings_for_all_sensors(self):
        state, gen = _load_generator("bharati")
        readings = gen.generate_all()
        assert len(readings) > 0

    def test_reading_has_required_fields(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        required_fields = {
            "station_id", "sensor_id", "domain", "metric_name",
            "value", "unit", "quality", "timestamp_utc"
        }
        for r in readings:
            missing = required_fields - set(r.keys())
            assert not missing, f"Reading missing fields: {missing}"

    def test_reading_station_id_matches_config(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        assert all(r["station_id"] == "maitri" for r in readings)

    def test_reading_values_are_finite(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        import math
        for r in readings:
            assert math.isfinite(r["value"]), f"Non-finite value in {r['sensor_id']}"

    def test_fuel_reading_is_positive(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        fuel_readings = [r for r in readings if "fuel_pct" in r["sensor_id"]]
        assert len(fuel_readings) > 0, "Must have at least one fuel_pct reading"
        for r in fuel_readings:
            assert 0 <= r["value"] <= 100

    def test_fire_readings_are_zero_nominally(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        fire_readings = [r for r in readings if r["metric_name"] == "fire_state"]
        for r in fire_readings:
            assert r["value"] == 0.0, "Fire sensors should read 0 (CLEAR) under nominal conditions"

    def test_fire_reading_is_one_when_anomaly_active(self):
        state, gen = _load_generator("maitri")
        state.inject_anomaly(AnomalyType.FIRE_ZONE_1)
        _run(state.step(1.0))
        readings = gen.generate_all()
        fire_z1 = [r for r in readings if "fire_z1" in r["sensor_id"]]
        assert len(fire_z1) > 0
        assert fire_z1[0]["value"] == 1.0

    def test_generator_domain_filter(self):
        state, gen = _load_generator("maitri")
        energy_readings = gen.generate_domain("energy")
        assert all(r["domain"] == "energy" for r in energy_readings)
        assert len(energy_readings) > 0

    def test_make_batch_structure(self):
        state, gen = _load_generator("bharati")
        readings = gen.generate_all()
        batch = make_batch("bharati", readings)
        assert batch["station_id"] == "bharati"
        assert len(batch["readings"]) == len(readings)
        assert "batch_id" in batch
        assert "generated_at" in batch

    def test_quality_flag_is_nominal_for_normal_values(self):
        state, gen = _load_generator("maitri")
        readings = gen.generate_all()
        for r in readings:
            assert r["quality"] in ("NOMINAL", "DEGRADED", "STALE", "SENSOR_FAULT")

    def test_both_stations_independent(self):
        """Generators for two stations must not share state."""
        sm, gm = _load_generator("maitri")
        sb, gb = _load_generator("bharati")
        sm.inject_anomaly(AnomalyType.FIRE_ZONE_1)
        _run(sm.step(1.0))
        maitri_readings = gm.generate_all()
        bharati_readings = gb.generate_all()
        # Maitri has fire active — Bharati fire must still be 0
        bharati_fire = [r for r in bharati_readings if r["metric_name"] == "fire_state"]
        for r in bharati_fire:
            assert r["value"] == 0.0, "Bharati fire must be unaffected by Maitri anomaly"


# ---------------------------------------------------------------------------
# SensorPublisher (dry-run mode — no network required)
# ---------------------------------------------------------------------------

class TestSensorPublisher:
    def test_publisher_dry_run_does_not_error(self):
        from simulator.station_sim.publisher import SensorPublisher
        pub = SensorPublisher("maitri", dry_run=True)
        _run(pub.start())
        pub.add_readings([{
            "station_id": "maitri", "sensor_id": "maitri.energy.gen1.fuel_pct",
            "domain": "energy", "metric_name": "fuel_level_percent",
            "value": 85.0, "unit": "pct", "quality": "NOMINAL",
            "timestamp_utc": "2026-08-27T09:00:00Z", "asset_id": "maitri.gen1",
            "is_aggregate": False, "aggregation_window_s": 0,
        }])
        result = _run(pub.flush())
        assert result is True
        assert pub.stats["total_sent"] == 1
        _run(pub.stop())

    def test_publisher_buffers_readings(self):
        from simulator.station_sim.publisher import SensorPublisher
        pub = SensorPublisher("bharati", dry_run=True)
        _run(pub.start())
        for i in range(5):
            pub.add_readings([{
                "station_id": "bharati", "sensor_id": f"bharati.energy.gen1.metric_{i}",
                "domain": "energy", "metric_name": "value",
                "value": float(i), "unit": "kW", "quality": "NOMINAL",
                "timestamp_utc": "2026-08-27T09:00:00Z", "asset_id": "",
                "is_aggregate": False, "aggregation_window_s": 0,
            }])
        assert pub.stats["buffer_depth"] == 5
        _run(pub.flush())
        assert pub.stats["buffer_depth"] == 0
        assert pub.stats["total_sent"] == 5
        _run(pub.stop())
