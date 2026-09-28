"""Insert a fresh batch of sensor readings with current timestamps.
Run this whenever the seeded data gets too old (> cutoff window).
Usage: PYTHONPATH=. python3 scripts/refresh_sensor_readings.py
"""
import asyncio
import os
import random
import ssl
import re
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(".env")


# Realistic sensor specs: (station_id, sensor_id, domain, unit, base_value, jitter)
SENSOR_SPECS = [
    # Maitri — Energy
    ("maitri", "maitri.generator.gen1.kw_output",  "energy", "kW",  142.0, 8.0),
    ("maitri", "maitri.generator.gen1.fuel_pct",   "energy", "%",   83.8,  1.0),
    ("maitri", "maitri.generator.gen1.load_pct",   "energy", "%",   86.0,  3.0),
    ("maitri", "maitri.power.grid.voltage",         "energy", "V",   415.0, 2.0),
    # Maitri — Weather
    ("maitri", "maitri.weather.aws1.temperature",  "weather", "°C", -28.4,  2.0),
    ("maitri", "maitri.weather.aws1.wind_speed",   "weather", "km/h", 67.0, 10.0),
    ("maitri", "maitri.weather.aws1.wind_dir",     "weather", "°",   220.0, 15.0),
    ("maitri", "maitri.weather.aws1.humidity",     "weather", "%",    78.0,  3.0),
    ("maitri", "maitri.weather.aws1.pressure",     "weather", "hPa", 978.4,  2.0),
    ("maitri", "maitri.weather.aws1.snowfall",     "weather", "mm/h",  0.8,  0.3),
    # Maitri — Seismic
    ("maitri", "maitri.seismic.sta1.pgv",       "seismic", "mm/s", 0.12, 0.05),
    ("maitri", "maitri.seismic.sta1.magnitude", "seismic", "ML",   0.8,  0.3),
    # Bharati — Energy
    ("bharati", "bharati.generator.gen1.kw_output", "energy", "kW",  185.0, 10.0),
    ("bharati", "bharati.generator.gen1.fuel_pct",  "energy", "%",   84.2,  1.0),
    ("bharati", "bharati.generator.gen1.load_pct",  "energy", "%",   88.0,  3.0),
    ("bharati", "bharati.power.grid.voltage",        "energy", "V",   415.0, 2.0),
    ("bharati", "bharati.solar.array1.kw_output",   "energy", "kW",  34.0,  4.0),
    # Bharati — Weather
    ("bharati", "bharati.weather.aws1.temperature", "weather", "°C", -21.7,  2.0),
    ("bharati", "bharati.weather.aws1.wind_speed",  "weather", "km/h", 42.0, 8.0),
    ("bharati", "bharati.weather.aws1.wind_dir",    "weather", "°",   180.0, 20.0),
    ("bharati", "bharati.weather.aws1.humidity",    "weather", "%",    85.0,  3.0),
    ("bharati", "bharati.weather.aws1.pressure",    "weather", "hPa", 1002.1, 2.0),
    ("bharati", "bharati.weather.aws1.snowfall",    "weather", "mm/h", 0.3,  0.2),
    ("bharati", "bharati.weather.aws1.radiation",   "weather", "W/m²", 120.0, 20.0),
]


async def refresh():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import text

    db_url = re.sub(
        r"[?&]sslmode=[^&]*|[?&]channel_binding=[^&]*",
        "",
        os.environ["CLOUD_DATABASE_URL"],
    ).rstrip("?&")
    engine = create_async_engine(
        db_url,
        connect_args={"ssl": ssl.create_default_context()},
        pool_size=2,
    )
    now = datetime.now(tz=timezone.utc)

    async with async_sessionmaker(engine, class_=AsyncSession)() as db:
        count = 0
        for station_id, sensor_id, domain, unit, base, jitter in SENSOR_SPECS:
            value = round(base + random.uniform(-jitter, jitter), 3)
            await db.execute(
                text("""
                    INSERT INTO sensor_readings
                        (station_id, sensor_id, domain, metric_name, value, unit, quality, timestamp_utc, is_aggregate)
                    VALUES
                        (:sid, :snid, :dom, :met, :val, :unit, 'NOMINAL', :ts, false)
                """),
                {
                    "sid": station_id,
                    "snid": sensor_id,
                    "dom": domain,
                    "met": sensor_id.rsplit(".", 1)[-1],
                    "val": value,
                    "unit": unit,
                    "ts": now,
                },
            )
            count += 1
        await db.commit()
        print(f"✅ Inserted {count} fresh readings at {now.isoformat()}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(refresh())
