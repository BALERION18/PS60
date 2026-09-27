"""Edge database schema — initial migration for Neon PostgreSQL.

Creates all tables present on the Edge (station-local) database.
TimescaleDB-specific DDL (hypertables, continuous aggregates, retention
policies) is intentionally absent — this migration targets standard
PostgreSQL 16 as provided by Neon.

Revision ID : 0001
Revises     : (none — initial revision)
Create Date : 2026-09-05
Branch      : edge
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = ("edge",)
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # sensor_readings
    # High-frequency time-series table (1 Hz writes per sensor).
    # Standard PG table with composite B-tree + BRIN indexes replaces
    # the TimescaleDB hypertable used in the full on-station deployment.
    # ------------------------------------------------------------------
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("sensor_id", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column(
            "quality", sa.String(32), nullable=False, server_default="NOMINAL"
        ),  # NOMINAL | DEGRADED | FAULT
        sa.Column("asset_id", sa.String(128), nullable=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_aggregate", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("aggregation_window_s", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Composite B-tree: primary query pattern — station + sensor + time range
    op.create_index(
        "ix_sensor_readings_station_sensor_time",
        "sensor_readings",
        ["station_id", "sensor_id", "timestamp_utc"],
        postgresql_ops={"timestamp_utc": "DESC"},
    )
    # Individual column indexes for flexible filtering
    op.create_index(
        "ix_sensor_readings_station_id", "sensor_readings", ["station_id"]
    )
    op.create_index(
        "ix_sensor_readings_sensor_id", "sensor_readings", ["sensor_id"]
    )
    # BRIN index: efficient for monotonically increasing timestamp columns
    op.create_index(
        "ix_sensor_readings_timestamp_brin",
        "sensor_readings",
        ["timestamp_utc"],
        postgresql_using="brin",
    )
    op.create_index(
        "ix_sensor_readings_domain", "sensor_readings", ["domain"]
    )

    # ------------------------------------------------------------------
    # alerts
    # Safety & operational alerts with full acknowledgment lifecycle.
    # ------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(128), primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        # CRITICAL | HIGH | MEDIUM | LOW
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("asset_id", sa.String(128), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("raw_sensor_snapshot", JSONB(), nullable=True),
        # Sensor values captured at the instant the alert fired
        sa.Column(
            "ack_state", sa.String(16), nullable=False, server_default="OPEN"
        ),  # OPEN | ACKNOWLEDGED | RESOLVED
        sa.Column("acknowledged_by", sa.String(128), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "black_box_activated",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("alert_id"),
    )
    op.create_index(
        "ix_alerts_station_severity_state",
        "alerts",
        ["station_id", "severity", "ack_state"],
    )
    op.create_index("ix_alerts_station_id", "alerts", ["station_id"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])
    op.create_index("ix_alerts_ack_state", "alerts", ["ack_state"])

    # ------------------------------------------------------------------
    # outbound_queue
    # Persistent store-and-forward queue for VSAT satellite transmission.
    # Priority lanes: 0=BlackBox, 1=Critical/High, 2=Med/Low, 3=Telemetry
    # ------------------------------------------------------------------
    op.create_table(
        "outbound_queue",
        sa.Column(
            "queue_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("message_type", sa.String(64), nullable=False),
        # ALERT | BLACK_BOX | TELEMETRY_BATCH
        sa.Column("payload_bytes", sa.LargeBinary(), nullable=False),
        # Zstd-compressed Protobuf binary
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acked_by_cloud", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_id", sa.String(128), nullable=True),
        # References alert_id, event_id, batch_id, etc.
        sa.PrimaryKeyConstraint("queue_id"),
    )
    op.create_index(
        "ix_outbound_queue_pending",
        "outbound_queue",
        ["acked_by_cloud", "priority", "created_at"],
    )
    op.create_index(
        "ix_outbound_queue_priority", "outbound_queue", ["priority"]
    )
    op.create_index(
        "ix_outbound_queue_station_id", "outbound_queue", ["station_id"]
    )

    # ------------------------------------------------------------------
    # black_box_frames
    # Tamper-evident, append-only flight-recorder frames.
    # Hash-chain: Frame 0 prev_hash = SHA-256(trigger_alert_id)
    #             Frame N prev_hash = frame_hash of Frame N-1
    # ------------------------------------------------------------------
    op.create_table(
        "black_box_frames",
        sa.Column(
            "frame_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("trigger_alert_id", sa.String(128), nullable=False),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("readings_protobuf", sa.LargeBinary(), nullable=False),
        # High-resolution Protobuf binary dump of sensor readings
        sa.Column("phase", sa.String(32), nullable=False),
        # PRE_EVENT | ACTIVE | POST_RESOLUTION
        sa.Column("prev_hash", sa.LargeBinary(32), nullable=False),
        # SHA-256 of frame N-1 (32 bytes)
        sa.Column("frame_hash", sa.LargeBinary(32), nullable=False),
        # SHA-256 of this frame (32 bytes)
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_partial_pre_event",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "window_closed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.PrimaryKeyConstraint("frame_id"),
        sa.UniqueConstraint(
            "event_id", "frame_index", name="uq_blackbox_event_frame"
        ),
    )
    op.create_index(
        "ix_blackbox_event_timestamp",
        "black_box_frames",
        ["event_id", "timestamp_utc"],
    )
    op.create_index(
        "ix_blackbox_station_id", "black_box_frames", ["station_id"]
    )
    op.create_index(
        "ix_blackbox_synced", "black_box_frames", ["synced_to_cloud"]
    )

    # ------------------------------------------------------------------
    # inventory_items
    # Consumables, fuel, spare parts, food, medical supplies.
    # ------------------------------------------------------------------
    op.create_table(
        "inventory_items",
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        # FUEL | SPARE_PARTS | FOOD | MEDICAL
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        # litres, kg, units
        sa.Column("min_safety_threshold", sa.Float(), nullable=True),
        sa.Column("daily_burn_rate", sa.Float(), nullable=True),
        # Estimated daily consumption rate
        sa.Column("days_remaining", sa.Integer(), nullable=True),
        # Derived from quantity / daily_burn_rate; may be pre-computed
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by", sa.String(128), nullable=False, server_default="'system'"
        ),
        sa.Column(
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index(
        "ix_inventory_items_station_id", "inventory_items", ["station_id"]
    )
    op.create_index(
        "ix_inventory_items_category", "inventory_items", ["category"]
    )

    # ------------------------------------------------------------------
    # asset_cache
    # Local read-only copy of the Cloud asset registry.
    # Populated on each successful Edge↔Cloud sync.
    # ------------------------------------------------------------------
    op.create_table(
        "asset_cache",
        sa.Column("asset_id", sa.String(128), primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        # BUILDING | GENERATOR | SOLAR_ARRAY | FUEL_TANK | ANTENNA | etc.
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="'ACTIVE'"
        ),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_index(
        "ix_asset_cache_station_id", "asset_cache", ["station_id"]
    )

    # ------------------------------------------------------------------
    # audit_log
    # Append-only audit trail for every write operation on the Edge.
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column(
            "entry_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=True),
        # null for system/background actions
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("request_body_hash", sa.String(64), nullable=True),
        # SHA-256 hex of request body
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(64), nullable=True),
        sa.Column(
            "timestamp_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index(
        "ix_audit_log_station_id", "audit_log", ["station_id"]
    )
    op.create_index(
        "ix_audit_log_timestamp_utc", "audit_log", ["timestamp_utc"]
    )

    # ------------------------------------------------------------------
    # link_status_log
    # Time-series record of Edge-to-Cloud VSAT link state.
    # ------------------------------------------------------------------
    op.create_table(
        "link_status_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("link_state", sa.String(16), nullable=False),
        # UP | DEGRADED | DOWN
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
        sa.Column("queue_depth_bytes", sa.BigInteger(), nullable=True),
        sa.Column("queue_item_count", sa.Integer(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_status_log_station_id", "link_status_log", ["station_id"]
    )
    op.create_index(
        "ix_link_status_log_recorded_at", "link_status_log", ["recorded_at"]
    )


def downgrade() -> None:
    op.drop_table("link_status_log")
    op.drop_table("audit_log")
    op.drop_table("asset_cache")
    op.drop_table("inventory_items")
    op.drop_table("black_box_frames")
    op.drop_table("outbound_queue")
    op.drop_table("alerts")
    op.drop_table("sensor_readings")
