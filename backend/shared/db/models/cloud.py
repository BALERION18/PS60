"""SQLAlchemy ORM models for the Cloud (NCPOR HQ) database.

Includes all Edge models (Cloud copies) plus Cloud-only entities:
resupply manifests, maintenance records, AI predictions, users/roles.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

# Use JSONB on PostgreSQL for indexing benefits; fall back to JSON on SQLite
_DB_URL = os.environ.get("DATABASE_URL", "")
if "postgresql" in _DB_URL or "postgres" in _DB_URL:
    from sqlalchemy.dialects.postgresql import JSONB as _JsonType
else:
    _JsonType = JSON  # type: ignore[assignment]

from sqlalchemy.orm import relationship

from shared.db.base import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Re-used from edge (Cloud copies with same schema)
# These are imported in migrations; declared here to keep Cloud models together.
# ---------------------------------------------------------------------------

from shared.db.models.edge import (
    SensorReading,
    Alert,
    BlackBoxFrame,
    InventoryItem,
    AuditLogEntry,
    LinkStatusRecord,
)

__all__ = [
    "SensorReading", "Alert", "BlackBoxFrame",
    "InventoryItem", "AuditLogEntry", "LinkStatusRecord",
    "Asset", "MaintenanceEvent", "ResupplyManifest",
    "ResupplyLineItem", "AIPrediction",
    "StationConnection", "StationConfig",
    "User", "Role", "UserRole",
]


# ---------------------------------------------------------------------------
# Infrastructure assets (Cloud primary; Edge caches a read-only copy)
# ---------------------------------------------------------------------------

class Asset(Base):
    """Station infrastructure asset for the 3D map and alert association."""
    __tablename__ = "assets"

    asset_id = Column(String(128), primary_key=True)
    station_id = Column(String(32), nullable=False, index=True)
    asset_type = Column(String(64), nullable=False)
    # Types: building, tunnel, tank, antenna, vehicle, generator, sensor_node
    name = Column(String(256), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation_m = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="ACTIVE")
    # Status: ACTIVE | DECOMMISSIONED | UNDER_MAINTENANCE
    metadata_json = Column(_JsonType, nullable=True)
    commissioned_at = Column(DateTime(timezone=True), nullable=True)
    decommissioned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    maintenance_events = relationship("MaintenanceEvent", back_populates="asset")

    __table_args__ = (
        Index("ix_assets_station_type", "station_id", "asset_type"),
    )


class MaintenanceEvent(Base):
    """Maintenance activity record associated with an infrastructure asset."""
    __tablename__ = "maintenance_events"

    event_id = Column(String(36), primary_key=True, default=_gen_uuid)
    asset_id = Column(String(128), ForeignKey("assets.asset_id"), nullable=False, index=True)
    station_id = Column(String(32), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    # Types: inspection, repair, replacement, calibration
    performed_at = Column(DateTime(timezone=True), nullable=False)
    technician = Column(String(256), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    asset = relationship("Asset", back_populates="maintenance_events")


# ---------------------------------------------------------------------------
# Logistics & resupply
# ---------------------------------------------------------------------------

class ResupplyManifest(Base):
    """A resupply expedition event delivering items to a station."""
    __tablename__ = "resupply_manifests"

    manifest_id = Column(String(36), primary_key=True, default=_gen_uuid)
    station_id = Column(String(32), nullable=False, index=True)
    expedition_name = Column(String(256), nullable=True)
    # e.g. "44th Indian Antarctic Expedition"
    voyage_year = Column(Integer, nullable=False)
    ship_name = Column(String(128), nullable=True)
    # e.g. "MV Vasiliy Golovnin"
    departure_date = Column(DateTime(timezone=True), nullable=True)
    arrival_window_start = Column(DateTime(timezone=True), nullable=True)
    arrival_window_end = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="PLANNED")
    # PLANNED | IN_TRANSIT | DELIVERED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_by = Column(String(128), nullable=True)

    line_items = relationship("ResupplyLineItem", back_populates="manifest")


class ResupplyLineItem(Base):
    """A single item delivered as part of a resupply manifest."""
    __tablename__ = "resupply_line_items"

    line_item_id = Column(String(36), primary_key=True, default=_gen_uuid)
    manifest_id = Column(String(36), ForeignKey("resupply_manifests.manifest_id"),
                         nullable=False, index=True)
    item_id = Column(String(128), nullable=False)  # references inventory_items.item_id
    item_name = Column(String(256), nullable=False)
    quantity_delivered = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)

    manifest = relationship("ResupplyManifest", back_populates="line_items")


# ---------------------------------------------------------------------------
# Cloud AI predictions
# ---------------------------------------------------------------------------

class AIPrediction(Base):
    """Output of a Cloud AI model run (fuel forecast, logistics demand, etc.)."""
    __tablename__ = "ai_predictions"

    prediction_id = Column(String(36), primary_key=True, default=_gen_uuid)
    station_id = Column(String(32), nullable=False, index=True)
    model_name = Column(String(128), nullable=False)
    # e.g. "fuel_depletion_prophet_v2", "vibration_anomaly"
    target_metric = Column(String(64), nullable=False)
    # e.g. "fuel_pct", "vibration_rms"
    predicted_for_date = Column(DateTime(timezone=True), nullable=True)
    predicted_value = Column(Float, nullable=True)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)
    risk_level = Column(String(16), nullable=False, default="NOMINAL")
    # NOMINAL | WARNING | CRITICAL
    predicted_json = Column(_JsonType, nullable=True)
    # For complex structured outputs (time-series forecast arrays, etc.)
    confidence = Column(Float, nullable=True)
    model_version = Column(String(64), nullable=True)
    data_window_start = Column(DateTime(timezone=True), nullable=True)
    data_window_end = Column(DateTime(timezone=True), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ai_predictions_station_model", "station_id", "model_name"),
    )


# ---------------------------------------------------------------------------
# Station connection tracking (Cloud-side)
# ---------------------------------------------------------------------------

class StationConnection(Base):
    """Current and historical link state for each station as seen from Cloud."""
    __tablename__ = "station_connections"

    station_id = Column(String(32), primary_key=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    link_state = Column(String(16), nullable=False, default="DOWN")
    # UP | DEGRADED | DOWN
    queue_depth_bytes = Column(BigInteger, nullable=True)
    open_critical_alerts = Column(Integer, nullable=True)
    open_high_alerts = Column(Integer, nullable=True)
    services_healthy = Column(Boolean, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Station runtime config (per-station threshold overrides stored in Cloud DB)
# ---------------------------------------------------------------------------

class StationConfig(Base):
    """Key-value configuration store for per-station runtime settings.

    Allows threshold overrides and feature flags without code deploys.
    """
    __tablename__ = "station_config"

    config_id = Column(String(36), primary_key=True, default=_gen_uuid)
    station_id = Column(String(32), nullable=False, index=True)
    config_key = Column(String(128), nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint("station_id", "config_key", name="uq_station_config_key"),
    )


# ---------------------------------------------------------------------------
# Users & RBAC
# ---------------------------------------------------------------------------

class User(Base):
    """Platform user with role-based access control."""
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=_gen_uuid)
    username = Column(String(128), nullable=False, unique=True)
    email = Column(String(256), nullable=True, unique=True)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    user_roles = relationship("UserRole", back_populates="user")


class Role(Base):
    """Available roles in the VajraX RBAC system."""
    __tablename__ = "roles"

    role_id = Column(String(36), primary_key=True, default=_gen_uuid)
    role_name = Column(String(64), nullable=False, unique=True)
    # ADMIN | OPERATOR | STATION_CREW | VIEWER
    description = Column(Text, nullable=True)

    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """Assignment of a role to a user, optionally scoped to a station."""
    __tablename__ = "user_roles"

    assignment_id = Column(String(36), primary_key=True, default=_gen_uuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.role_id"), nullable=False, index=True)
    station_scope = Column(String(32), nullable=True)
    # null = global; "maitri" or "bharati" = station-scoped
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    assigned_by = Column(String(128), nullable=True)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "station_scope", name="uq_user_role_scope"),
    )
