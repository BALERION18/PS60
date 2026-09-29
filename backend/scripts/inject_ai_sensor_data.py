"""Inject realistic sensor readings that the AI models can actually use.

The existing seeded data uses different sensor ID conventions from what
the YAML config and AI models expect. This script inserts:

  1. Normal baseline readings (last 7 days) — Models 2 & 4 use 7d trends
  2. Degraded readings (last 24 hours) — triggers WARNING/CRITICAL outputs
  3. Fuel level readings — makes fuel tab show live tank level

Sensor IDs match exactly what the models look for (from maitri.yaml):
  maitri.energy.gen1.fuel_pct
  maitri.energy.gen1.power_output_kw
  maitri.energy.gen1.fuel_consumption_lph
  maitri.energy.gen1.oil_pressure_bar
  maitri.energy.gen1.coolant_temp_c
  maitri.energy.gen1.vibration_rms       (custom — used by IF model)
  maitri.energy.gen2.power_output_kw
  maitri.energy.grid.total_load_kw
  maitri.weather.aws.ambient_temp_c
  maitri.weather.aws.wind_speed_ms

  bharati.energy.gen1.*  (same pattern)
"""
from __future__ import annotations

import asyncio
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
load_dotenv(str(_BACKEND / ".env"))


# ---------------------------------------------------------------------------
# Sensor definitions — (station, sensor_id, domain, metric_name, unit, ...)
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(tz=timezone.utc)

def _ts(seconds_ago: int) -> datetime:
    return _now() - timedelta(seconds=seconds_ago)


async def inject():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text

    raw_url = os.environ.get("CLOUD_DATABASE_URL", "")
    db_url = re.sub(r"[?&]sslmode=[^&]*|[?&]channel_binding=[^&]*", "", raw_url).rstrip("?&")

    engine = create_async_engine(db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    rng = random.Random(42)

    print("\n" + "="*60)
    print("  INJECTING AI-COMPATIBLE SENSOR READINGS")
    print("="*60)

    async with Session() as session:

        # ------------------------------------------------------------------
        # 1. Clear old AI-sensor readings to avoid duplicates
        # ------------------------------------------------------------------
        await session.execute(text("""
            DELETE FROM sensor_readings
            WHERE sensor_id LIKE '%.energy.gen%.%'
               OR sensor_id LIKE '%.energy.grid.%'
               OR sensor_id LIKE '%.weather.aws.%'
        """))
        await session.commit()
        print("\n  Cleared old AI sensor rows.")

        # ------------------------------------------------------------------
        # 2. Build reading rows
        # ------------------------------------------------------------------
        rows = []

        # Helper to add a reading
        def reading(station, sensor_id, domain, metric, unit, value, ts):
            rows.append({
                "station_id":  station,
                "sensor_id":   sensor_id,
                "domain":      domain,
                "metric_name": metric,
                "value":       round(value, 3),
                "unit":        unit,
                "quality":     "NOMINAL",
                "asset_id":    None,
                "timestamp_utc": ts,
                "is_aggregate":  False,
                "aggregation_window_s": None,
            })

        # ------------------------------------------------------------------
        # MAITRI — 7 days of normal baseline (every 10 minutes)
        # ------------------------------------------------------------------
        print("\n  Generating Maitri 7-day baseline (normal operation)...")
        interval_s = 600  # 10 minutes
        n_normal   = 7 * 24 * 6  # 7 days × 6 readings/hour

        for i in range(n_normal, 0, -1):
            ts = _ts(i * interval_s)
            load = 95 + rng.gauss(0, 5)

            reading("maitri", "maitri.energy.gen1.fuel_pct",          "energy", "fuel_level_percent",   "pct",  83.0 - i*0.002 + rng.gauss(0, 0.2), ts)
            reading("maitri", "maitri.energy.gen1.power_output_kw",   "energy", "power_output_kw",      "kW",   load + rng.gauss(0, 3), ts)
            reading("maitri", "maitri.energy.gen1.fuel_consumption_lph","energy","fuel_consumption_lph", "L/h",  load * 0.0047 + rng.gauss(0, 0.1), ts)
            reading("maitri", "maitri.energy.gen1.oil_pressure_bar",  "energy", "oil_pressure_bar",     "bar",  4.5 + rng.gauss(0, 0.1), ts)
            reading("maitri", "maitri.energy.gen1.coolant_temp_c",    "energy", "coolant_temp_c",       "degC", 85 + rng.gauss(0, 1.5), ts)
            reading("maitri", "maitri.energy.gen1.vibration_rms",     "energy", "vibration_rms",        "mm/s", 3.2 + rng.gauss(0, 0.4), ts)
            reading("maitri", "maitri.energy.gen2.power_output_kw",   "energy", "power_output_kw",      "kW",   40 + rng.gauss(0, 2), ts)
            reading("maitri", "maitri.energy.grid.total_load_kw",     "energy", "total_load_kw",        "kW",   load * 1.45 + rng.gauss(0, 4), ts)
            reading("maitri", "maitri.weather.aws.ambient_temp_c",    "weather","ambient_temp_c",       "degC", -28.4 + rng.gauss(0, 1.5), ts)
            reading("maitri", "maitri.weather.aws.wind_speed_ms",     "weather","wind_speed_ms",        "m/s",  8.5 + rng.gauss(0, 1.5), ts)

        print(f"    {n_normal * 10} rows queued (7 days × 10 sensors)")

        # ------------------------------------------------------------------
        # MAITRI — Last 24 hours: BEARING WEAR DEVELOPING
        # Generator DG-1 shows rising vibration + oil pressure drop
        # This should trigger IF anomaly + RF HIGH maintenance
        # ------------------------------------------------------------------
        print("\n  Generating Maitri last-24h degraded readings (bearing wear)...")
        n_degraded = 24 * 6  # 24h × 6/hr

        for i in range(n_degraded, 0, -1):
            ts   = _ts(i * interval_s)
            prog = (n_degraded - i) / n_degraded   # 0→1 as time progresses
            load = 98 + rng.gauss(0, 5)

            # Vibration creeping up: 3.2 → 14.5 mm/s (bearing wear signature)
            vib  = 3.2 + prog * 11.3 + rng.gauss(0, 0.6)
            # Oil pressure slowly dropping: 4.5 → 2.8 bar (seal wear)
            oil  = 4.5 - prog * 1.7 + rng.gauss(0, 0.08)
            # Coolant slightly elevated: 85 → 92°C (friction heat)
            cool = 85 + prog * 7 + rng.gauss(0, 1.0)

            reading("maitri", "maitri.energy.gen1.fuel_pct",          "energy", "fuel_level_percent",   "pct",  83.0 - i*0.003 + rng.gauss(0, 0.15), ts)
            reading("maitri", "maitri.energy.gen1.power_output_kw",   "energy", "power_output_kw",      "kW",   load + rng.gauss(0, 3), ts)
            reading("maitri", "maitri.energy.gen1.fuel_consumption_lph","energy","fuel_consumption_lph","L/h",  load * 0.0055 + rng.gauss(0, 0.15), ts)
            reading("maitri", "maitri.energy.gen1.oil_pressure_bar",  "energy", "oil_pressure_bar",     "bar",  oil, ts)
            reading("maitri", "maitri.energy.gen1.coolant_temp_c",    "energy", "coolant_temp_c",       "degC", cool, ts)
            reading("maitri", "maitri.energy.gen1.vibration_rms",     "energy", "vibration_rms",        "mm/s", vib, ts)
            reading("maitri", "maitri.energy.gen2.power_output_kw",   "energy", "power_output_kw",      "kW",   40 + rng.gauss(0, 2), ts)
            reading("maitri", "maitri.energy.grid.total_load_kw",     "energy", "total_load_kw",        "kW",   load * 1.45 + rng.gauss(0, 4), ts)
            reading("maitri", "maitri.weather.aws.ambient_temp_c",    "weather","ambient_temp_c",       "degC", -28.4 + rng.gauss(0, 1.5), ts)
            reading("maitri", "maitri.weather.aws.wind_speed_ms",     "weather","wind_speed_ms",        "m/s",  8.5 + rng.gauss(0, 1.5), ts)

        print(f"    {n_degraded * 10} rows queued (24h degraded — vib: 3→14 mm/s, oil: 4.5→2.8 bar)")

        # ------------------------------------------------------------------
        # BHARATI — 7 days normal baseline
        # ------------------------------------------------------------------
        print("\n  Generating Bharati 7-day baseline...")
        for i in range(n_normal, 0, -1):
            ts   = _ts(i * interval_s)
            load = 150 + rng.gauss(0, 8)
            solar = max(0, 18 + rng.gauss(0, 5))

            reading("bharati", "bharati.energy.gen1.fuel_pct",          "energy","fuel_level_percent",   "pct",  84.2 - i*0.002 + rng.gauss(0, 0.2), ts)
            reading("bharati", "bharati.energy.gen1.power_output_kw",   "energy","power_output_kw",      "kW",   load + rng.gauss(0, 4), ts)
            reading("bharati", "bharati.energy.gen1.fuel_consumption_lph","energy","fuel_consumption_lph","L/h", load * 0.006 + rng.gauss(0, 0.15), ts)
            reading("bharati", "bharati.energy.gen1.vibration_rms",     "energy","vibration_rms",        "mm/s", 3.8 + rng.gauss(0, 0.5), ts)
            reading("bharati", "bharati.energy.solar1.output_kw",       "energy","solar_output_kw",      "kW",   solar, ts)
            reading("bharati", "bharati.energy.grid.total_load_kw",     "energy","total_load_kw",        "kW",   load * 1.5 + rng.gauss(0, 6), ts)
            reading("bharati", "bharati.weather.aws.ambient_temp_c",    "weather","ambient_temp_c",      "degC", -21.7 + rng.gauss(0, 1.5), ts)
            reading("bharati", "bharati.weather.aws.wind_speed_ms",     "weather","wind_speed_ms",       "m/s",  9.2 + rng.gauss(0, 2), ts)

        print(f"    {n_normal * 8} rows queued (7 days × 8 sensors)")

        # ------------------------------------------------------------------
        # BHARATI — Last 24h: COOLANT OVERTEMP developing
        # ------------------------------------------------------------------
        print("\n  Generating Bharati last-24h degraded readings (coolant overtemp)...")
        for i in range(n_degraded, 0, -1):
            ts   = _ts(i * interval_s)
            prog = (n_degraded - i) / n_degraded
            load = 155 + rng.gauss(0, 6)

            # Coolant rising: 88 → 108°C
            cool = 88 + prog * 20 + rng.gauss(0, 1.2)
            # Vibration slightly elevated (mechanical stress from overtemp)
            vib  = 3.8 + prog * 5 + rng.gauss(0, 0.5)

            reading("bharati", "bharati.energy.gen1.fuel_pct",          "energy","fuel_level_percent",   "pct",  84.2 - i*0.003 + rng.gauss(0, 0.15), ts)
            reading("bharati", "bharati.energy.gen1.power_output_kw",   "energy","power_output_kw",      "kW",   load + rng.gauss(0, 4), ts)
            reading("bharati", "bharati.energy.gen1.fuel_consumption_lph","energy","fuel_consumption_lph","L/h", load * 0.007 + rng.gauss(0, 0.2), ts)
            reading("bharati", "bharati.energy.gen1.vibration_rms",     "energy","vibration_rms",        "mm/s", vib, ts)
            reading("bharati", "bharati.energy.solar1.output_kw",       "energy","solar_output_kw",      "kW",   max(0, 18 + rng.gauss(0, 5)), ts)
            reading("bharati", "bharati.energy.grid.total_load_kw",     "energy","total_load_kw",        "kW",   load * 1.5 + rng.gauss(0, 5), ts)
            reading("bharati", "bharati.weather.aws.ambient_temp_c",    "weather","ambient_temp_c",      "degC", -21.7 + rng.gauss(0, 1.5), ts)
            reading("bharati", "bharati.weather.aws.wind_speed_ms",     "weather","wind_speed_ms",       "m/s",  9.2 + rng.gauss(0, 2), ts)

        print(f"    {n_degraded * 8} rows queued (24h degraded — coolant: 88→108°C)")

        # ------------------------------------------------------------------
        # 3. Bulk insert all rows
        # ------------------------------------------------------------------
        total = len(rows)
        print(f"\n  Inserting {total:,} rows into sensor_readings...")

        BATCH = 500
        inserted = 0
        for start in range(0, total, BATCH):
            batch = rows[start:start + BATCH]
            await session.execute(
                text("""
                    INSERT INTO sensor_readings
                        (station_id, sensor_id, domain, metric_name, value,
                         unit, quality, asset_id, timestamp_utc,
                         is_aggregate, aggregation_window_s)
                    VALUES
                        (:station_id, :sensor_id, :domain, :metric_name, :value,
                         :unit, :quality, :asset_id, :timestamp_utc,
                         :is_aggregate, :aggregation_window_s)
                """),
                batch,
            )
            inserted += len(batch)
            print(f"    {inserted:,}/{total:,} inserted...", end="\r")

        await session.commit()
        print(f"\n  All {total:,} rows committed.        ")

    await engine.dispose()

    print("\n" + "="*60)
    print("  DONE — Refresh the Analytics page to see live model output")
    print("="*60)
    print("\n  What to expect:")
    print("  Maitri  → Anomaly: WARNING/CRITICAL (bearing wear + oil drop)")
    print("  Maitri  → Maintenance: HIGH urgency (bearing inspection)")
    print("  Bharati → Anomaly: WARNING (coolant overtemp)")
    print("  Bharati → Maintenance: MEDIUM urgency (cooling system check)")
    print("  Fuel tab → Real tank % from latest fuel_pct reading")
    print()


if __name__ == "__main__":
    asyncio.run(inject())
