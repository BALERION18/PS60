"""Cloud service configuration — reads from environment variables.

Database URL priority:
  1. CLOUD_DATABASE_URL  (Neon PostgreSQL — preferred)
  2. DATABASE_URL        (generic fallback)
  If neither is set, startup will raise RuntimeError from the DB engine.

CORS (production):
  Set ALLOWED_ORIGINS to a comma-separated list of allowed frontend URLs.
  Example: ALLOWED_ORIGINS=https://vajrax.vercel.app,http://localhost:5173
  Default: allows all origins (dev convenience — restrict in production!).

Station public keys (production on Railway):
  Set STATION_PUBKEY_{STATION_ID.upper()} to the PEM string for each station.
  If not set, a throwaway in-memory keypair is generated (dev/demo mode).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional


class CloudConfig:
    """Typed configuration for all Cloud (NCPOR HQ) services."""

    station_ids: List[str]
    database_url: str
    db_echo: bool
    redis_url: str
    jwt_secret: str
    jwt_access_expire_minutes: int
    jwt_refresh_expire_days: int
    mqtt_enabled: bool           # set MQTT_ENABLED=false to suppress broker warnings
    mqtt_host: str
    mqtt_port: int
    mqtt_tls: bool
    station_pubkey_dir: str       # optional — directory containing {station_id}_public.pem
    heartbeat_timeout_minutes: int
    api_host: str
    api_port: int
    log_level: str
    log_json: bool
    allowed_origins: List[str]   # CORS allowed origins — restrict in production

    def __init__(self) -> None:
        raw_ids = os.environ.get("STATION_IDS", "maitri,bharati")
        self.station_ids = [s.strip().lower() for s in raw_ids.split(",") if s.strip()]

        # Neon URL (CLOUD_DATABASE_URL) takes priority over the generic DATABASE_URL
        db_url = (
            os.environ.get("CLOUD_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
        )
        if not db_url:
            raise RuntimeError(
                "No cloud database URL configured. "
                "Set CLOUD_DATABASE_URL in your environment / Railway env vars."
            )
        self.database_url = db_url
        self.db_echo = os.environ.get("DB_ECHO", "false").lower() == "true"

        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        self.jwt_secret = os.environ.get("CLOUD_JWT_SECRET", "")
        if not self.jwt_secret:
            raise RuntimeError(
                "CLOUD_JWT_SECRET is not set. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\" "
                "and add it to Railway environment variables."
            )
        self.jwt_access_expire_minutes = int(
            os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "60")
        )
        self.jwt_refresh_expire_days = int(
            os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7")
        )

        self.mqtt_enabled = os.environ.get("MQTT_ENABLED", "false").lower() == "true"
        # Support both MQTT_BROKER_HOST (preferred) and legacy MQTT_HOST
        self.mqtt_host = (
            os.environ.get("MQTT_BROKER_HOST")
            or os.environ.get("MQTT_HOST", "localhost")
        )
        self.mqtt_port = int(
            os.environ.get("MQTT_BROKER_PORT")
            or os.environ.get("MQTT_PORT", "1883")
        )
        # Support both MQTT_USE_TLS (preferred) and legacy MQTT_TLS
        _tls_raw = (
            os.environ.get("MQTT_USE_TLS")
            or os.environ.get("MQTT_TLS", "false")
        )
        self.mqtt_tls = _tls_raw.lower() == "true"

        # Station pubkey directory — used only if env-var PEM strings are not set
        self.station_pubkey_dir = os.environ.get("STATION_PUBKEY_DIR", "")

        self.heartbeat_timeout_minutes = int(
            os.environ.get("HEARTBEAT_TIMEOUT_MINUTES", "15")
        )

        self.api_host = os.environ.get("API_HOST", "0.0.0.0")
        self.api_port = int(os.environ.get("CLOUD_API_PORT", "8200"))

        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.log_json = os.environ.get("LOG_FORMAT", "json") == "json"

        # CORS — allowed origins for the frontend
        raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
        if raw_origins.strip():
            self.allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        else:
            # Default: allow all (dev convenience). Set ALLOWED_ORIGINS in production!
            self.allowed_origins = ["*"]

    def pubkey_path(self, station_id: str) -> str:
        """Path to Ed25519 public key file for a given station (filesystem fallback)."""
        if not self.station_pubkey_dir:
            return ""
        return os.path.join(self.station_pubkey_dir, f"{station_id}_public.pem")

    def __repr__(self) -> str:
        # Mask credentials in repr to avoid leaking to logs
        safe_db = self.database_url.split("@")[-1] if "@" in self.database_url else "…"
        return f"CloudConfig(stations={self.station_ids}, db=…@{safe_db}, origins={self.allowed_origins})"


@lru_cache(maxsize=1)
def get_config() -> CloudConfig:
    """Return the singleton CloudConfig (initialised once, cached thereafter)."""
    return CloudConfig()
