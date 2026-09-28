"""Edge Backend — FastAPI application entry point.

This is the main process running at each Antarctic research station.
It starts all background services on startup and shuts them down cleanly.

Services started in order:
  1. Database engine (async SQLAlchemy + TimescaleDB)
  2. Redis client (for queue, pub/sub, dedup cache)
  3. Station config (YAML)
  4. Alert Engine (background asyncio task)
  5. Black-Box Logger (background asyncio task)

FastAPI routers mounted:
  - /ingest              → edge.ingestion.router
  - /api/v1/local/...   → edge.api.router

Usage:
  STATION_ID=maitri DATABASE_URL=postgresql://... REDIS_URL=redis://... \\
      uvicorn edge.main:app --host 0.0.0.0 --port 8100
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.db.async_base import get_async_engine, get_async_session_factory
from shared.schemas.config import StationConfig
from shared.utils.logging import configure_logging
from edge.alert_engine.service import AlertEngine
from edge.api.router import router as local_api_router
from edge.auth.local_auth import KeyStore, set_key_store
from edge.black_box.service import BlackBoxLogger
from edge.config import get_config
from edge.deps import set_engine, set_station_id
from edge.ingestion.router import router as ingestion_router
from edge.redis_client import close_redis, init_redis

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_cfg_tmp_log = os.environ.get("LOG_FORMAT", "json")
configure_logging(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    json_output=_cfg_tmp_log == "json",
)
log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    log.info("edge.startup", station_id=cfg.station_id, port=cfg.ingest_port)

    # 1. Database
    engine = get_async_engine(cfg.database_url, echo=cfg.db_echo)
    session_factory = get_async_session_factory(engine)
    set_engine(engine)
    set_station_id(cfg.station_id)

    # 2. Redis
    await init_redis(cfg.redis_url)

    # 3. Station config
    station_config = StationConfig.from_yaml(cfg.station_config_path)
    log.info(
        "edge.config_loaded",
        station_id=cfg.station_id,
        sensors=len(station_config.sensors),
        threshold_rules=len(station_config.threshold_rules),
    )

    # 3a. Local auth KeyStore (offline — uses pre-provisioned keys from YAML)
    key_store = KeyStore(station_config.local_api_keys)
    set_key_store(key_store)
    log.info("edge.auth.key_store_ready", station_id=cfg.station_id)

    # 4. Alert Engine
    alert_engine = AlertEngine(
        station_id=cfg.station_id,
        config=station_config,
        session_factory=session_factory,
        dedup_ttl_s=cfg.alert_dedup_ttl_s,
    )
    await alert_engine.start()
    app.state.alert_engine = alert_engine

    # 5. Black-Box Logger
    black_box_logger = BlackBoxLogger(
        station_id=cfg.station_id,
        session_factory=session_factory,
        pre_event_s=cfg.black_box_pre_event_s,
        post_resolution_s=cfg.black_box_post_resolution_s,
        frame_interval_s=cfg.black_box_frame_interval_s,
    )
    await black_box_logger.start()
    app.state.black_box_logger = black_box_logger

    log.info("edge.ready", station_id=cfg.station_id)
    yield  # app runs

    # --------------- Shutdown ---------------
    log.info("edge.shutdown", station_id=cfg.station_id)
    await black_box_logger.stop()
    await alert_engine.stop()
    await close_redis()
    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=f"VajraX Edge Backend",
    description=(
        "Edge-local API for Antarctic research station operations. "
        "Provides sensor ingestion, alert management, and local dashboard data."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened per-deployment; fine for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ingestion_router)
app.include_router(local_api_router)


# ---------------------------------------------------------------------------
# Root health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health():
    cfg = get_config()
    return {
        "status": "ok",
        "station_id": cfg.station_id,
        "display_name": cfg.display_name,
        "service": "edge-backend",
        "version": "1.0.0",
    }
