"""Edge local REST API router.

All routes are station-local (no station_id in path — this Edge knows its own identity).
Mounted at /api/v1/local/ on the Edge FastAPI application.

Auth: Bearer <ROLE.secret> — pre-provisioned API keys loaded from station config.
  - GET  endpoints → any authenticated role (CREW | OPERATOR | ADMIN)
  - PATCH/acknowledge → OPERATOR | ADMIN
  - PATCH/resolve     → OPERATOR | ADMIN  (CRITICAL alerts are ops-only)

Endpoints:
  GET  /api/v1/local/status                    Station health summary
  GET  /api/v1/local/alerts                    List alerts (filterable)
  GET  /api/v1/local/alerts/{alert_id}         Alert detail
  PATCH /api/v1/local/alerts/{alert_id}/acknowledge  Acknowledge an alert
  PATCH /api/v1/local/alerts/{alert_id}/resolve      Resolve a CRITICAL alert (manual)
  GET  /api/v1/local/sensors                   Latest reading per sensor
  GET  /api/v1/local/sensors/{sensor_id}       Time-series for one sensor
  GET  /api/v1/local/inventory                 Inventory items
  PATCH /api/v1/local/inventory/{item_id}      Update inventory quantity
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.edge import Alert, InventoryItem, SensorReading
from edge.api.schemas import (
    AlertAcknowledgeIn,
    AlertOut,
    InventoryItemOut,
    PaginatedResponse,
    SensorReadingOut,
    StationStatusOut,
)
from edge.auth.local_auth import require_any, require_operator
from edge.deps import get_db_session, get_station_id
from edge.redis_client import get_redis
from shared.utils.time import utcnow

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/local", tags=["edge-local-api"])

# Service start time (module-level for uptime calculation)
_start_time: float = time.monotonic()


# ---------------------------------------------------------------------------
# Station status
# ---------------------------------------------------------------------------

@router.get("/status", response_model=StationStatusOut)
async def get_station_status(
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> StationStatusOut:
    """Return a concise health summary for the station crew dashboard."""
    # Count open alerts by severity
    severity_counts: Dict[str, int] = {}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        result = await session.execute(
            select(func.count(Alert.alert_id))
            .where(Alert.station_id == station_id)
            .where(Alert.severity == sev)
            .where(Alert.ack_state != "RESOLVED")
        )
        severity_counts[sev] = result.scalar_one() or 0

    # Latest reading per sensor (last 5 minutes)
    cutoff = utcnow() - timedelta(minutes=5)
    latest_result = await session.execute(
        select(SensorReading.sensor_id, func.max(SensorReading.value))
        .where(SensorReading.station_id == station_id)
        .where(SensorReading.timestamp_utc >= cutoff)
        .group_by(SensorReading.sensor_id)
        .limit(50)
    )
    latest_readings = {row[0]: row[1] for row in latest_result.all()}

    # Redis health
    redis_ok = True
    try:
        redis = get_redis()
        await redis.ping()
    except Exception:
        redis_ok = False

    from edge.config import get_config
    cfg = get_config()

    return StationStatusOut(
        station_id=station_id,
        display_name=cfg.display_name,
        uptime_s=time.monotonic() - _start_time,
        open_critical=severity_counts.get("CRITICAL", 0),
        open_high=severity_counts.get("HIGH", 0),
        open_medium=severity_counts.get("MEDIUM", 0),
        open_low=severity_counts.get("LOW", 0),
        latest_readings=latest_readings,
        link_state="UNKNOWN",  # populated by sync agent in Phase 3
        db_healthy=True,
        redis_healthy=redis_ok,
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=PaginatedResponse)
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    ack_state: Optional[str] = Query(None, description="Filter by ack_state"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> PaginatedResponse:
    """List alerts with optional severity/state/domain filters, paginated."""
    q = select(Alert).where(Alert.station_id == station_id)
    if severity:
        q = q.where(Alert.severity == severity.upper())
    if ack_state:
        q = q.where(Alert.ack_state == ack_state.upper())
    if domain:
        q = q.where(Alert.domain == domain.lower())

    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one() or 0

    q = q.order_by(Alert.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AlertOut.model_validate(r) for r in rows],
    )


@router.get("/alerts/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> AlertOut:
    result = await session.execute(
        select(Alert)
        .where(Alert.alert_id == alert_id)
        .where(Alert.station_id == station_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id!r} not found")
    return AlertOut.model_validate(alert)


@router.patch("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: str,
    body: AlertAcknowledgeIn,
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_operator),
) -> AlertOut:
    """Acknowledge an alert. Requires OPERATOR or ADMIN role."""
    result = await session.execute(
        select(Alert)
        .where(Alert.alert_id == alert_id)
        .where(Alert.station_id == station_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id!r} not found")
    if alert.ack_state == "RESOLVED":
        raise HTTPException(status_code=409, detail="Alert is already resolved")

    alert.ack_state = "ACKNOWLEDGED"
    alert.acknowledged_by = body.acknowledged_by
    alert.acknowledged_at = utcnow()
    await session.commit()
    await session.refresh(alert)

    log.info(
        "edge.api.alert_acknowledged",
        alert_id=alert_id,
        by=body.acknowledged_by,
        station_id=station_id,
    )
    return AlertOut.model_validate(alert)


@router.patch("/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: str,
    body: AlertAcknowledgeIn,
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_operator),
) -> AlertOut:
    """Manually resolve a CRITICAL alert after crew intervention. Requires OPERATOR or ADMIN."""
    result = await session.execute(
        select(Alert)
        .where(Alert.alert_id == alert_id)
        .where(Alert.station_id == station_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id!r} not found")
    if alert.ack_state == "RESOLVED":
        raise HTTPException(status_code=409, detail="Alert is already resolved")

    alert.ack_state = "RESOLVED"
    alert.resolved_at = utcnow()
    alert.acknowledged_by = body.acknowledged_by
    await session.commit()
    await session.refresh(alert)

    # Publish resolution so black-box window can begin post-resolution countdown
    import json
    redis = get_redis()
    from edge.redis_client import alerts_channel
    await redis.publish(
        alerts_channel(station_id),
        json.dumps({
            "alert_id": alert_id,
            "station_id": station_id,
            "ack_state": "RESOLVED",
            "resolved_at": alert.resolved_at.isoformat(),
            "auto_resolved": False,
        }),
    )

    log.info(
        "edge.api.alert_manually_resolved",
        alert_id=alert_id,
        by=body.acknowledged_by,
        station_id=station_id,
    )
    return AlertOut.model_validate(alert)


# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------

@router.get("/sensors", response_model=List[SensorReadingOut])
async def get_latest_readings(
    domain: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> List[SensorReadingOut]:
    """Return the most recent reading for each sensor (last 5 minutes)."""
    cutoff = utcnow() - timedelta(minutes=5)
    subq = (
        select(
            SensorReading.sensor_id,
            func.max(SensorReading.timestamp_utc).label("max_ts"),
        )
        .where(SensorReading.station_id == station_id)
        .where(SensorReading.timestamp_utc >= cutoff)
    )
    if domain:
        subq = subq.where(SensorReading.domain == domain.lower())
    subq = subq.group_by(SensorReading.sensor_id).subquery()

    result = await session.execute(
        select(SensorReading)
        .join(
            subq,
            (SensorReading.sensor_id == subq.c.sensor_id)
            & (SensorReading.timestamp_utc == subq.c.max_ts),
        )
        .order_by(SensorReading.sensor_id)
    )
    rows = result.scalars().all()
    return [SensorReadingOut.model_validate(r) for r in rows]


@router.get("/sensors/{sensor_id}", response_model=List[SensorReadingOut])
async def get_sensor_history(
    sensor_id: str,
    hours: float = Query(1.0, ge=0.1, le=168.0, description="Hours of history to return"),
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> List[SensorReadingOut]:
    """Return time-series readings for one sensor over the last N hours."""
    cutoff = utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(SensorReading)
        .where(SensorReading.station_id == station_id)
        .where(SensorReading.sensor_id == sensor_id)
        .where(SensorReading.timestamp_utc >= cutoff)
        .order_by(SensorReading.timestamp_utc)
        .limit(10000)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No readings for sensor {sensor_id!r} in the last {hours}h",
        )
    return [SensorReadingOut.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@router.get("/inventory", response_model=List[InventoryItemOut])
async def list_inventory(
    category: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
    _auth: dict = Depends(require_any),
) -> List[InventoryItemOut]:
    q = select(InventoryItem).where(InventoryItem.station_id == station_id)
    if category:
        q = q.where(InventoryItem.category == category.lower())
    rows = (await session.execute(q.order_by(InventoryItem.category, InventoryItem.name))).scalars().all()
    return [InventoryItemOut.model_validate(r) for r in rows]
