"""Cloud FastAPI application entry point.

Startup sequence (lifespan):
  1. Configure structured logging
  2. Init async DB engine (postgresql+asyncpg)
  3. Init Cloud Redis pool (or in-memory mock when unavailable)
  4. Load Ed25519 public keys for each station:
       - First checks STATION_PUBKEY_{STATION_ID.upper()} env var (production)
       - Falls back to generating throwaway in-memory keypairs (dev)
  5. Build CloudIngestionService
  6. Build WebSocketManager + start Redis pub/sub listener
  7. Build CloudMQTTSubscriber + start background MQTT task
  8. Inject engine into cloud/deps.py

Shutdown sequence (reverse):
  1. Stop MQTT subscriber
  2. Stop WebSocket Redis listener
  3. Close Redis pool
  4. Dispose DB engine

Mounted routes:
  /api/v1/hq/*  — HQ dashboard REST API
  /ws           — WebSocket live feed
  /health       — global health check
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# ── Load .env before any config module is imported ─────────────────────────
try:
    from dotenv import load_dotenv
    # Try backend/.env first, then root .env — silently skip if neither exists
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
    else:
        _root_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if _root_env.exists():
            load_dotenv(_root_env, override=False)
except ImportError:
    pass  # python-dotenv not installed — env vars must be set in shell

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.crypto.signing import Verifier, generate_station_keypair
from shared.db.async_base import get_async_engine
from shared.utils.logging import configure_logging
from cloud.auth.router import router as auth_router
from cloud.config import get_config
from cloud.deps import set_engine
from cloud.ingestion.service import CloudIngestionService
from cloud.middleware.audit_log import AuditLogMiddleware
from cloud.middleware.security import SecurityHeadersMiddleware
from cloud.redis_client import close_redis, init_redis, init_mock_redis
from cloud.websocket.manager import WebSocketManager
from cloud.websocket.router import router as ws_router, set_manager
from cloud.api.router import router as hq_router

log = structlog.get_logger(__name__)


def _load_station_verifiers(cfg) -> dict[str, Verifier]:
    """Load Ed25519 public keys for each configured station.

    Priority (for each station_id):
      1. STATION_PUBKEY_{STATION_ID.upper()} environment variable (PEM string)
         → Use in production on Railway; set via Railway env vars dashboard.
      2. File on disk at cfg.station_pubkey_dir (legacy / local dev with files)
      3. Generate a throwaway in-memory keypair (dev fallback — keys lost on restart)
    """
    verifiers: dict[str, Verifier] = {}

    for station_id in cfg.station_ids:
        station_id_upper = station_id.upper().replace("-", "_")
        env_var_name = f"STATION_PUBKEY_{station_id_upper}"

        # 1. Try env var (production path — no filesystem needed)
        pem_str = os.environ.get(env_var_name, "").strip()
        if pem_str:
            # Env vars can't contain literal newlines in Railway dashboard;
            # allow the PEM to be stored with \n escaped as literal backslash-n
            pem_bytes = pem_str.replace("\\n", "\n").encode("utf-8")
            verifiers[station_id] = Verifier.from_pem_bytes(pem_bytes)
            log.info("cloud.startup.key_from_env", station_id=station_id, env_var=env_var_name)
            continue

        # 2. Try filesystem (local dev with actual PEM files)
        if cfg.station_pubkey_dir:
            pub_path = cfg.pubkey_path(station_id)
            if os.path.exists(pub_path):
                verifiers[station_id] = Verifier.from_pem_file(pub_path)
                log.info("cloud.startup.key_from_file", station_id=station_id, path=pub_path)
                continue

        # 3. Generate throwaway in-memory keypair (dev fallback)
        log.warning(
            "cloud.startup.keygen_throwaway",
            station_id=station_id,
            hint=(
                f"Set {env_var_name} env var (PEM string) for persistent keys. "
                "Using a throwaway keypair — real station data will fail signature verification."
            ),
        )
        _priv_pem, pub_pem = generate_station_keypair()
        verifiers[station_id] = Verifier.from_pem_bytes(pub_pem)

    return verifiers


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    cfg = get_config()
    configure_logging(level=cfg.log_level, json_output=cfg.log_json)
    log.info("cloud.startup.begin", stations=cfg.station_ids)

    # 1. DB
    engine = get_async_engine(cfg.database_url, echo=cfg.db_echo)
    set_engine(engine)

    # 2. Redis (optional — falls back to in-memory mock; no crash on Railway)
    redis_ok = False
    try:
        await init_redis(cfg.redis_url)
        redis_ok = True
    except Exception as exc:
        log.warning(
            "cloud.startup.redis_unavailable",
            error=str(exc),
            hint="Using in-memory Redis mock. Refresh tokens won't persist across restarts.",
        )
        await init_mock_redis()

    # 3. Station public keys
    verifiers = _load_station_verifiers(cfg)

    # 4. Ingestion service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ingestion_svc = CloudIngestionService(
        session_factory=session_factory,
        verifiers=verifiers,
    )

    # 5. WebSocket manager (optional — needs Redis pub/sub)
    ws_manager = None
    if redis_ok:
        try:
            ws_manager = WebSocketManager()
            set_manager(ws_manager)
            await ws_manager.start_redis_listener()
        except Exception as exc:
            log.warning("cloud.startup.ws_unavailable", error=str(exc))
            ws_manager = None

    # 6. MQTT subscriber (only started when MQTT_ENABLED=true)
    mqtt_sub = None
    if cfg.mqtt_enabled:
        try:
            from cloud.mqtt_subscriber import CloudMQTTSubscriber  # lazy import
            mqtt_sub = CloudMQTTSubscriber(
                host=cfg.mqtt_host,
                port=cfg.mqtt_port,
                ingestion_service=ingestion_svc,
                tls=cfg.mqtt_tls,
            )
            await mqtt_sub.start()
        except Exception as exc:
            log.warning(
                "cloud.startup.mqtt_unavailable",
                error=str(exc),
                hint="Check MQTT_BROKER_HOST / MQTT_PORT. Station sync disabled.",
            )
            mqtt_sub = None
    else:
        log.info(
            "cloud.mqtt.disabled",
            hint="Set MQTT_ENABLED=true in env to enable live edge-station sync.",
        )

    log.info("cloud.startup.done", redis=redis_ok, mqtt=mqtt_sub is not None)
    yield

    # --- Shutdown ---
    if mqtt_sub:
        await mqtt_sub.stop()
    if ws_manager:
        await ws_manager.stop()
    if redis_ok:
        await close_redis()
    await engine.dispose()
    log.info("cloud.shutdown.done")


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title="VajraX — Cloud Backend (NCPOR HQ)",
        description="Digital Twin cloud backend for Maitri & Bharati Antarctic Research Stations",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — restrict to configured origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Security / audit middleware (added after CORS so it runs innermost)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth_router)
    app.include_router(hq_router)
    app.include_router(ws_router)

    @app.get("/health", tags=["health"])
    async def root_health() -> dict:
        return {"status": "ok", "service": "vajrax-cloud", "stations": cfg.station_ids}

    return app


app = create_app()
