"""Pydantic response schemas for the Edge local API.

These are the wire types returned by the Edge local REST API.
They are separate from the ORM models to allow clean field selection
and computed fields (e.g., duration_open_s on alerts).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field

from shared.utils.time import utcnow


class SensorReadingOut(BaseModel):
    sensor_id: str
    domain: str
    metric_name: str
    value: float
    unit: str
    quality: str
    asset_id: Optional[str]
    timestamp_utc: datetime

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    alert_id: str
    station_id: str
    severity: str
    domain: str
    asset_id: Optional[str] = None
    triggered_at: datetime
    description: str
    ack_state: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    black_box_activated: bool = False
    synced_to_cloud: bool = False

    @computed_field
    @property
    def duration_open_s(self) -> float:
        """Seconds the alert has been open (0 if resolved)."""
        if self.resolved_at:
            return (self.resolved_at - self.triggered_at).total_seconds()
        return (utcnow() - self.triggered_at).total_seconds()

    model_config = {"from_attributes": True}


class AlertAcknowledgeIn(BaseModel):
    acknowledged_by: str


class StationStatusOut(BaseModel):
    station_id: str
    display_name: str
    uptime_s: float
    open_critical: int
    open_high: int
    open_medium: int
    open_low: int
    latest_readings: Dict[str, float]   # sensor_id → latest value
    link_state: str                      # UP | DEGRADED | DOWN
    db_healthy: bool
    redis_healthy: bool


class InventoryItemOut(BaseModel):
    item_id: str
    station_id: str
    category: str
    name: str
    quantity: float
    unit: str
    min_threshold: Optional[float]
    last_updated: datetime
    updated_by: str

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any]
