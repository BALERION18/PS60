"""Cloud database schema — initial migration for Neon PostgreSQL.

Creates all tables present in the Cloud (NCPOR HQ) database, including:
  - Mirrored copies of Edge tables (sensor_readings, alerts, black_box_frames,
    inventory_items, audit_log, link_status_log, outbound_queue, asset_cache)
  - Cloud-only tables: assets, maintenance_events, resupply_manifests,
    resupply_line_items, ai_predictions, station_connections, station_config
  - RBAC: users, roles, user_roles

Seed data inserted at the end of upgrade():
  - 4 canonical roles (ADMIN, OPERATOR, STATION_CREW, VIEWER)
  - 2 station_connections rows (maitri + bharati — initial state: DOWN)
  - 16 infrastructure assets (8 per station)
  - 1 admin user (username: admin, password: admin123  — bcrypt hash)

Revision ID : 0002
Revises     : (none — independent cloud branch)
Create Date : 2026-09-05
Branch      : cloud
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = None
branch_labels = ("cloud",)
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    # ------------------------------------------------------------------
    # sensor_readings  (cloud mirror — same schema as edge)
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
        ),
        sa.Column("asset_id", sa.String(128), nullable=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_aggregate", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("aggregation_window_s", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sr_station_sensor_time",
        "sensor_readings",
        ["station_id", "sensor_id", "timestamp_utc"],
        postgresql_ops={"timestamp_utc": "DESC"},
    )
    op.create_index(
        "ix_sr_timestamp_brin",
        "sensor_readings",
        ["timestamp_utc"],
        postgresql_using="brin",
    )
    op.create_index("ix_sr_station_id", "sensor_readings", ["station_id"])
    op.create_index("ix_sr_domain", "sensor_readings", ["domain"])

    # ------------------------------------------------------------------
    # alerts  (cloud mirror)
    # ------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(128), primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("asset_id", sa.String(128), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("raw_sensor_snapshot", JSONB(), nullable=True),
        sa.Column(
            "ack_state", sa.String(16), nullable=False, server_default="OPEN"
        ),
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
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="true"
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
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])

    # ------------------------------------------------------------------
    # black_box_frames  (cloud mirror — tamper-evident hash chain)
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
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("prev_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("frame_hash", sa.LargeBinary(32), nullable=False),
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
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.PrimaryKeyConstraint("frame_id"),
        sa.UniqueConstraint(
            "event_id", "frame_index", name="uq_blackbox_event_frame"
        ),
    )
    op.create_index(
        "ix_bbf_event_timestamp",
        "black_box_frames",
        ["event_id", "timestamp_utc"],
    )

    # ------------------------------------------------------------------
    # inventory_items  (cloud mirror)
    # ------------------------------------------------------------------
    op.create_table(
        "inventory_items",
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("min_safety_threshold", sa.Float(), nullable=True),
        sa.Column("daily_burn_rate", sa.Float(), nullable=True),
        sa.Column("days_remaining", sa.Integer(), nullable=True),
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
            "synced_to_cloud", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index(
        "ix_inv_station_category", "inventory_items", ["station_id", "category"]
    )

    # ------------------------------------------------------------------
    # audit_log  (cloud mirror + cloud-generated entries)
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
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("request_body_hash", sa.String(64), nullable=True),
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
        "ix_audit_log_station_time", "audit_log", ["station_id", "timestamp_utc"]
    )

    # ------------------------------------------------------------------
    # link_status_log  (cloud mirror)
    # ------------------------------------------------------------------
    op.create_table(
        "link_status_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("link_state", sa.String(16), nullable=False),
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
        "ix_link_status_station", "link_status_log", ["station_id"]
    )
    op.create_index(
        "ix_link_status_recorded_at",
        "link_status_log",
        ["recorded_at"],
        postgresql_using="brin",
    )

    # ------------------------------------------------------------------
    # assets
    # Infrastructure digital twin registry (Cloud primary; Edge caches a
    # read-only copy as asset_cache). Includes geospatial coordinates for
    # the 3-D map view.
    # ------------------------------------------------------------------
    op.create_table(
        "assets",
        sa.Column("asset_id", sa.String(128), primary_key=True),
        # e.g. 'maitri.building.main_block'
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        # BUILDING | GENERATOR | SOLAR_ARRAY | FUEL_TANK | ANTENNA | VEHICLE | SENSOR_NODE
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="'ACTIVE'"
        ),
        # ACTIVE | UNDER_MAINTENANCE | DECOMMISSIONED
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column("commissioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decommissioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_index(
        "ix_assets_station_type", "assets", ["station_id", "asset_type"]
    )
    op.create_index("ix_assets_station_id", "assets", ["station_id"])

    # ------------------------------------------------------------------
    # maintenance_events
    # Inspection, repair, calibration records tied to assets.
    # ------------------------------------------------------------------
    op.create_table(
        "maintenance_events",
        sa.Column(
            "event_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column(
            "asset_id",
            sa.String(128),
            sa.ForeignKey("assets.asset_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        # inspection | repair | replacement | calibration
        sa.Column("performed_by", sa.String(256), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_maintenance_events_asset_id", "maintenance_events", ["asset_id"]
    )
    op.create_index(
        "ix_maintenance_events_station_id", "maintenance_events", ["station_id"]
    )

    # ------------------------------------------------------------------
    # resupply_manifests
    # Annual expedition logistics — one row per resupply voyage.
    # ------------------------------------------------------------------
    op.create_table(
        "resupply_manifests",
        sa.Column(
            "manifest_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("expedition_name", sa.String(256), nullable=True),
        # e.g. "44th Indian Antarctic Expedition"
        sa.Column("voyage_year", sa.Integer(), nullable=False),
        sa.Column("ship_name", sa.String(128), nullable=True),
        # e.g. "MV Vasiliy Golovnin"
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("arrival_window_start", sa.Date(), nullable=True),
        sa.Column("arrival_window_end", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="'PLANNED'"
        ),
        # PLANNED | IN_TRANSIT | DELIVERED
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint("manifest_id"),
    )
    op.create_index(
        "ix_resupply_manifests_station_id",
        "resupply_manifests",
        ["station_id"],
    )
    op.create_index(
        "ix_resupply_manifests_voyage_year",
        "resupply_manifests",
        ["voyage_year"],
    )

    # ------------------------------------------------------------------
    # resupply_line_items
    # Individual items within a resupply manifest.
    # ------------------------------------------------------------------
    op.create_table(
        "resupply_line_items",
        sa.Column(
            "line_item_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column(
            "manifest_id",
            sa.String(36),
            sa.ForeignKey("resupply_manifests.manifest_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(128), nullable=False),
        # references inventory_items.item_id
        sa.Column("item_name", sa.String(256), nullable=False),
        sa.Column("quantity_delivered", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("line_item_id"),
    )
    op.create_index(
        "ix_resupply_line_items_manifest_id",
        "resupply_line_items",
        ["manifest_id"],
    )

    # ------------------------------------------------------------------
    # ai_predictions
    # Outputs of Cloud AI models (fuel depletion, vibration anomaly, etc.)
    # ------------------------------------------------------------------
    op.create_table(
        "ai_predictions",
        sa.Column(
            "prediction_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        # e.g. 'fuel_depletion_prophet_v2' | 'vibration_anomaly'
        sa.Column("target_metric", sa.String(64), nullable=False),
        sa.Column("predicted_for_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("predicted_value", sa.Float(), nullable=True),
        sa.Column("confidence_lower", sa.Float(), nullable=True),
        sa.Column("confidence_upper", sa.Float(), nullable=True),
        sa.Column(
            "risk_level", sa.String(16), nullable=False, server_default="'NOMINAL'"
        ),
        # NOMINAL | WARNING | CRITICAL
        sa.Column("predicted_json", JSONB(), nullable=True),
        # For complex structured outputs (e.g. time-series forecast arrays)
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("data_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("prediction_id"),
    )
    op.create_index(
        "ix_ai_predictions_station_model",
        "ai_predictions",
        ["station_id", "model_name"],
    )
    op.create_index(
        "ix_ai_predictions_generated_at", "ai_predictions", ["generated_at"]
    )

    # ------------------------------------------------------------------
    # station_connections
    # Live heartbeat + link health summary per station (Cloud-side).
    # ------------------------------------------------------------------
    op.create_table(
        "station_connections",
        sa.Column("station_id", sa.String(32), primary_key=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "link_state", sa.String(16), nullable=False, server_default="'DOWN'"
        ),
        # UP | DEGRADED | DOWN
        sa.Column("queue_depth_bytes", sa.BigInteger(), nullable=True),
        sa.Column("open_critical_alerts", sa.Integer(), nullable=True),
        sa.Column("open_high_alerts", sa.Integer(), nullable=True),
        sa.Column("services_healthy", sa.Boolean(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("station_id"),
    )

    # ------------------------------------------------------------------
    # station_config
    # Key-value threshold overrides and feature flags per station.
    # Allows runtime changes without code deploys.
    # ------------------------------------------------------------------
    op.create_table(
        "station_config",
        sa.Column(
            "config_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("station_id", sa.String(32), nullable=False),
        sa.Column("config_key", sa.String(128), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_by", sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint("config_id"),
        sa.UniqueConstraint(
            "station_id", "config_key", name="uq_station_config_key"
        ),
    )
    op.create_index(
        "ix_station_config_station_id", "station_config", ["station_id"]
    )

    # ------------------------------------------------------------------
    # users
    # Platform users for Cloud RBAC (NCPOR HQ login).
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(256), nullable=True, unique=True),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ------------------------------------------------------------------
    # roles
    # Available RBAC roles in VajraX.
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column(
            "role_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("role_name", sa.String(64), nullable=False, unique=True),
        # ADMIN | OPERATOR | STATION_CREW | VIEWER
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("role_id"),
    )

    # ------------------------------------------------------------------
    # user_roles
    # Assignment of a role to a user, optionally scoped to a station.
    # station_scope = NULL  → global access across all stations
    # station_scope = 'maitri' | 'bharati' → station-scoped access only
    # ------------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column(
            "assignment_id",
            sa.String(36),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.role_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("station_scope", sa.String(32), nullable=True),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("assigned_by", sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint("assignment_id"),
        sa.UniqueConstraint(
            "user_id", "role_id", "station_scope", name="uq_user_role_scope"
        ),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # ==========================================================================
    # Seed data
    # ==========================================================================
    now = _now()

    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Seed: roles
    # ------------------------------------------------------------------
    role_rows = [
        {
            "role_id": _uuid(),
            "role_name": "ADMIN",
            "description": (
                "Full platform access — can manage users, stations, and configuration."
            ),
        },
        {
            "role_id": _uuid(),
            "role_name": "OPERATOR",
            "description": (
                "Operational access — can acknowledge alerts, update inventory, "
                "and view all telemetry."
            ),
        },
        {
            "role_id": _uuid(),
            "role_name": "STATION_CREW",
            "description": (
                "On-station crew — limited to read-only telemetry and alert "
                "acknowledgment for their assigned station."
            ),
        },
        {
            "role_id": _uuid(),
            "role_name": "VIEWER",
            "description": (
                "Read-only access — can view dashboards and reports but cannot "
                "modify any data."
            ),
        },
    ]
    bind.execute(
        sa.text(
            "INSERT INTO roles (role_id, role_name, description) "
            "VALUES (:role_id, :role_name, :description)"
        ),
        role_rows,
    )

    # ------------------------------------------------------------------
    # Seed: station_connections (both stations start as DOWN)
    # ------------------------------------------------------------------
    bind.execute(
        sa.text(
            "INSERT INTO station_connections "
            "(station_id, link_state, open_critical_alerts, open_high_alerts, "
            " services_healthy, updated_at) "
            "VALUES (:station_id, 'DOWN', 0, 0, false, :updated_at)"
        ),
        [
            {"station_id": "maitri", "updated_at": now},
            {"station_id": "bharati", "updated_at": now},
        ],
    )

    # ------------------------------------------------------------------
    # Seed: assets — 8 per station (16 total)
    # Coordinates are approximate real-world values for each station.
    # ------------------------------------------------------------------
    maitri_assets = [
        {
            "asset_id": "maitri.generator.gen1",
            "asset_type": "GENERATOR",
            "name": "Maitri Diesel Generator #1",
            "latitude": -70.7671,
            "longitude": 11.7328,
            "elevation_m": 117.0,
            "metadata_json": '{"fuel_type":"diesel","rated_kw":100}',
        },
        {
            "asset_id": "maitri.generator.gen2",
            "asset_type": "GENERATOR",
            "name": "Maitri Diesel Generator #2",
            "latitude": -70.7672,
            "longitude": 11.7330,
            "elevation_m": 117.0,
            "metadata_json": '{"fuel_type":"diesel","rated_kw":100}',
        },
        {
            "asset_id": "maitri.power.grid",
            "asset_type": "POWER_GRID",
            "name": "Maitri Station Power Distribution Grid",
            "latitude": -70.7671,
            "longitude": 11.7329,
            "elevation_m": 117.0,
            "metadata_json": '{"phases":3,"voltage_v":415}',
        },
        {
            "asset_id": "maitri.weather.aws1",
            "asset_type": "SENSOR_NODE",
            "name": "Maitri Automatic Weather Station",
            "latitude": -70.7680,
            "longitude": 11.7340,
            "elevation_m": 119.0,
            "metadata_json": '{"sensors":["temperature","wind_speed","wind_dir","pressure","humidity"]}',
        },
        {
            "asset_id": "maitri.building.main_block",
            "asset_type": "BUILDING",
            "name": "Maitri Main Living Block",
            "latitude": -70.7670,
            "longitude": 11.7325,
            "elevation_m": 117.0,
            "metadata_json": '{"floors":2,"capacity_persons":25}',
        },
        {
            "asset_id": "maitri.building.lab",
            "asset_type": "BUILDING",
            "name": "Maitri Science Laboratory",
            "latitude": -70.7673,
            "longitude": 11.7332,
            "elevation_m": 117.5,
            "metadata_json": '{"labs":["glaciology","meteorology","seismology"]}',
        },
        {
            "asset_id": "maitri.tank.fuel_main",
            "asset_type": "FUEL_TANK",
            "name": "Maitri Main Fuel Storage Tank",
            "latitude": -70.7665,
            "longitude": 11.7318,
            "elevation_m": 116.5,
            "metadata_json": '{"capacity_litres":200000,"fuel_type":"diesel"}',
        },
        {
            "asset_id": "maitri.seismic.station1",
            "asset_type": "SENSOR_NODE",
            "name": "Maitri Seismic Monitoring Station",
            "latitude": -70.7690,
            "longitude": 11.7350,
            "elevation_m": 120.0,
            "metadata_json": '{"sensors":["seismic_x","seismic_y","seismic_z"]}',
        },
    ]

    bharati_assets = [
        {
            "asset_id": "bharati.generator.gen1",
            "asset_type": "GENERATOR",
            "name": "Bharati Diesel Generator #1",
            "latitude": -69.4072,
            "longitude": 76.1929,
            "elevation_m": 35.0,
            "metadata_json": '{"fuel_type":"diesel","rated_kw":160}',
        },
        {
            "asset_id": "bharati.generator.gen2",
            "asset_type": "GENERATOR",
            "name": "Bharati Diesel Generator #2",
            "latitude": -69.4073,
            "longitude": 76.1932,
            "elevation_m": 35.0,
            "metadata_json": '{"fuel_type":"diesel","rated_kw":160}',
        },
        {
            "asset_id": "bharati.solar.array1",
            "asset_type": "SOLAR_ARRAY",
            "name": "Bharati Solar Panel Array",
            "latitude": -69.4060,
            "longitude": 76.1915,
            "elevation_m": 34.0,
            "metadata_json": '{"panels":48,"rated_kwp":12}',
        },
        {
            "asset_id": "bharati.weather.aws1",
            "asset_type": "SENSOR_NODE",
            "name": "Bharati Automatic Weather Station",
            "latitude": -69.4085,
            "longitude": 76.1945,
            "elevation_m": 36.0,
            "metadata_json": '{"sensors":["temperature","wind_speed","wind_dir","pressure","humidity","radiation"]}',
        },
        {
            "asset_id": "bharati.building.main_block",
            "asset_type": "BUILDING",
            "name": "Bharati Main Research Building",
            "latitude": -69.4072,
            "longitude": 76.1928,
            "elevation_m": 35.0,
            "metadata_json": '{"floors":3,"capacity_persons":47}',
        },
        {
            "asset_id": "bharati.building.lab",
            "asset_type": "BUILDING",
            "name": "Bharati Science Laboratory Wing",
            "latitude": -69.4075,
            "longitude": 76.1935,
            "elevation_m": 35.5,
            "metadata_json": '{"labs":["oceanography","glaciology","atmospheric"]}',
        },
        {
            "asset_id": "bharati.tank.fuel_main",
            "asset_type": "FUEL_TANK",
            "name": "Bharati Main Fuel Storage Tank",
            "latitude": -69.4065,
            "longitude": 76.1920,
            "elevation_m": 34.5,
            "metadata_json": '{"capacity_litres":350000,"fuel_type":"diesel"}',
        },
        {
            "asset_id": "bharati.antenna.vsat",
            "asset_type": "ANTENNA",
            "name": "Bharati VSAT Satellite Communication Antenna",
            "latitude": -69.4068,
            "longitude": 76.1922,
            "elevation_m": 36.0,
            "metadata_json": '{"bandwidth_mhz":4,"protocol":"DVB-S2","provider":"ISRO"}',
        },
    ]

    all_assets = []
    for a in maitri_assets:
        all_assets.append(
            {
                "asset_id": a["asset_id"],
                "station_id": "maitri",
                "asset_type": a["asset_type"],
                "name": a["name"],
                "latitude": a["latitude"],
                "longitude": a["longitude"],
                "elevation_m": a["elevation_m"],
                "status": "ACTIVE",
                "metadata_json": a["metadata_json"],
                "commissioned_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )
    for a in bharati_assets:
        all_assets.append(
            {
                "asset_id": a["asset_id"],
                "station_id": "bharati",
                "asset_type": a["asset_type"],
                "name": a["name"],
                "latitude": a["latitude"],
                "longitude": a["longitude"],
                "elevation_m": a["elevation_m"],
                "status": "ACTIVE",
                "metadata_json": a["metadata_json"],
                "commissioned_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )

    bind.execute(
        sa.text(
            "INSERT INTO assets "
            "(asset_id, station_id, asset_type, name, latitude, longitude, "
            " elevation_m, status, metadata_json, commissioned_at, created_at, updated_at) "
            "VALUES (:asset_id, :station_id, :asset_type, :name, :latitude, :longitude, "
            "        :elevation_m, :status, :metadata_json, :commissioned_at, "
            "        :created_at, :updated_at)"
        ),
        all_assets,
    )

    # ------------------------------------------------------------------
    # Seed: admin user
    # Password: admin123  (bcrypt $2b$12$ hash)
    # Change this immediately in production!
    # ------------------------------------------------------------------
    admin_id = _uuid()
    admin_role_row = bind.execute(
        sa.text("SELECT role_id FROM roles WHERE role_name = 'ADMIN' LIMIT 1")
    ).fetchone()

    bind.execute(
        sa.text(
            "INSERT INTO users "
            "(user_id, username, email, hashed_password, is_active, created_at) "
            "VALUES (:user_id, :username, :email, :hashed_password, true, :created_at)"
        ),
        [
            {
                "user_id": admin_id,
                "username": "admin",
                "email": "admin@vajrax.ncpor.in",
                # bcrypt hash of "admin123" (cost factor 12)
                "hashed_password": (
                    "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lek6OOT"
                    "NVNxOmwXi"
                ),
                "created_at": now,
            }
        ],
    )

    if admin_role_row:
        bind.execute(
            sa.text(
                "INSERT INTO user_roles "
                "(assignment_id, user_id, role_id, station_scope, assigned_at, assigned_by) "
                "VALUES (:assignment_id, :user_id, :role_id, NULL, :assigned_at, 'system')"
            ),
            [
                {
                    "assignment_id": _uuid(),
                    "user_id": admin_id,
                    "role_id": admin_role_row[0],
                    "assigned_at": now,
                }
            ],
        )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("station_config")
    op.drop_table("station_connections")
    op.drop_table("ai_predictions")
    op.drop_table("resupply_line_items")
    op.drop_table("resupply_manifests")
    op.drop_table("maintenance_events")
    op.drop_table("assets")
    op.drop_table("link_status_log")
    op.drop_table("audit_log")
    op.drop_table("inventory_items")
    op.drop_table("black_box_frames")
    op.drop_table("alerts")
    op.drop_table("sensor_readings")
