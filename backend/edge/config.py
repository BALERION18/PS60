"""Edge service configuration — reads from environment variables.

All Edge services (ingestion, alert engine, black-box logger, API, sync agent)
import this single config object. It is constructed once at module import time
from environment variables set in the project .env file.

Database URL priority:
  1. EDGE_DATABASE_URL  (Neon PostgreSQL — preferred for dev)
  2. DATABASE_URL       (generic fallback)
"""
from __future__ import annotations

import os
from functools import lru_cache


class EdgeConfig:
    """Typed configuration for all Edge services."""

    # ---------------------------------------------------------------------------
    # Station identity
    # ---------------------------------------------------------------------------
    station_id: str
    display_name: str

    # ---------------------------------------------------------------------------
    # Database
    # ---------------------------------------------------------------------------
    database_url: str      # postgresql://user:pass@host:port/dbname
    db_echo: bool          # log SQL statements (dev only)

    # ---------------------------------------------------------------------------
    # Redis
    # ---------------------------------------------------------------------------
    redis_url: str         # redis://host:port/0

    # ---------------------------------------------------------------------------
    # Ingestion
    # ---------------------------------------------------------------------------
    ingest_host: str
    ingest_port: int
    ingest_max_batch_size: int  # max readings per POST body

    # ---------------------------------------------------------------------------
    # Alert engine
    # ---------------------------------------------------------------------------
    alert_dedup_ttl_s: int      # seconds to suppress duplicate alerts (same sensor+rule)
    alert_heartbeat_s: int      # interval for link-health heartbeat check

    # ---------------------------------------------------------------------------
    # Black-box logger
    # ---------------------------------------------------------------------------
    black_box_pre_event_s: int          # capture window before trigger (seconds)
    black_box_post_resolution_s: int    # keep window open after resolution (seconds)
    black_box_frame_interval_s: int     # write one frame per this many seconds
    black_box_max_retention_days: int   # purge events older than this

    # ---------------------------------------------------------------------------
    # Sync agent
    # ---------------------------------------------------------------------------
    mqtt_host: str
    mqtt_port: int
    mqtt_tls: bool
    mqtt_keepalive_s: int
    queue_max_bytes: int        # max Redis queue size before overflow eviction
    queue_retention_days: int   # TTL for priority-3 telemetry items

    # ---------------------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------------------
    log_level: str
    log_json: bool

    # ---------------------------------------------------------------------------
    # Station config YAML
    # ---------------------------------------------------------------------------
    station_config_path: str

    def __init__(self) -> None:
        self.station_id = os.environ["STATION_ID"].strip().lower()
        if self.station_id not in ("maitri", "bharati"):
            raise RuntimeError(
                f"STATION_ID must be 'maitri' or 'bharati', got: {self.station_id!r}"
            )
        self.display_name = {
            "maitri": "Maitri Research Station",
            "bharati": "Bharati Research Station",
        }[self.station_id]

        # EDGE_DATABASE_URL (Neon) takes priority over the generic DATABASE_URL
        db_url = (
            os.environ.get("EDGE_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
        )
        if not db_url:
            raise RuntimeError(
                "No edge database URL configured. "
                "Set EDGE_DATABASE_URL in your .env file."
            )
        self.database_url = db_url
        self.db_echo = os.environ.get("DB_ECHO", "false").lower() == "true"

        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        self.ingest_host = os.environ.get("INGEST_HOST", "0.0.0.0")
        self.ingest_port = int(os.environ.get("INGEST_PORT", "8100"))
        self.ingest_max_batch_size = int(os.environ.get("INGEST_MAX_BATCH_SIZE", "500"))

        self.alert_dedup_ttl_s = int(os.environ.get("ALERT_DEDUP_TTL_S", "300"))
        self.alert_heartbeat_s = int(os.environ.get("ALERT_HEARTBEAT_S", "60"))

        self.black_box_pre_event_s = int(os.environ.get("BLACK_BOX_PRE_EVENT_S", "300"))
        self.black_box_post_resolution_s = int(
            os.environ.get("BLACK_BOX_POST_RESOLUTION_S", "900")
        )
        self.black_box_frame_interval_s = int(
            os.environ.get("BLACK_BOX_FRAME_INTERVAL_S", "10")
        )
        self.black_box_max_retention_days = int(
            os.environ.get("BLACK_BOX_RETENTION_DAYS", "30")
        )

        self.mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_PORT", "18883"))
        self.mqtt_tls = os.environ.get("MQTT_TLS", "true").lower() == "true"
        self.mqtt_keepalive_s = int(os.environ.get("MQTT_KEEPALIVE_S", "60"))
        self.queue_max_bytes = int(
            os.environ.get("QUEUE_MAX_BYTES", str(512 * 1024 * 1024))  # 512 MB
        )
        self.queue_retention_days = int(os.environ.get("QUEUE_RETENTION_DAYS", "30"))

        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.log_json = os.environ.get("LOG_FORMAT", "json") == "json"

        self.station_config_path = os.environ.get(
            "STATION_CONFIG_PATH",
            f"edge/config/{self.station_id}.yaml",
        )

    def __repr__(self) -> str:
        return (
            f"EdgeConfig(station_id={self.station_id!r}, "
            f"db={self.database_url!r}, redis={self.redis_url!r})"
        )


@lru_cache(maxsize=1)
def get_config() -> EdgeConfig:
    """Return the singleton EdgeConfig (cached after first call)."""
    return EdgeConfig()
