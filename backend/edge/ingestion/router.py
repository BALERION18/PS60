"""FastAPI router for the Edge ingestion endpoint.

Mounted at the root level of the Edge FastAPI app.
All state (DB engine, Redis) is injected via FastAPI dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from edge.deps import get_db_session, get_station_id
from edge.ingestion.service import IngestionService

log = structlog.get_logger(__name__)
router = APIRouter(tags=["ingestion"])


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class SensorReadingIn(BaseModel):
    station_id: str
    sensor_id: str
    domain: str
    metric_name: str
    value: float
    unit: str
    quality: str = "NOMINAL"
    asset_id: Optional[str] = None
    timestamp_utc: str
    is_aggregate: bool = False
    aggregation_window_s: Optional[int] = None


class SensorBatchIn(BaseModel):
    station_id: str
    readings: List[SensorReadingIn] = Field(..., max_length=500)
    batch_id: Optional[str] = None
    generated_at: Optional[str] = None
    sequence_number: Optional[int] = None
    is_aggregate: bool = False
    aggregation_window_s: Optional[int] = None


class IngestResponse(BaseModel):
    accepted: int
    batch_id: Optional[str]
    station_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a sensor batch from the station simulator or hardware driver",
)
async def ingest_batch(
    batch: SensorBatchIn,
    session: AsyncSession = Depends(get_db_session),
    station_id: str = Depends(get_station_id),
) -> IngestResponse:
    """Accept a SensorBatch, persist all readings, and publish to Redis.

    Returns HTTP 202 Accepted after DB write and Redis publish succeed.
    Station ID mismatch returns HTTP 400.
    """
    if batch.station_id != station_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch station_id {batch.station_id!r} does not match "
                f"this Edge station {station_id!r}"
            ),
        )

    svc = IngestionService(session, station_id)
    raw_batch = batch.model_dump()
    raw_batch["readings"] = [r.model_dump() for r in batch.readings]

    count = await svc.ingest(raw_batch)
    return IngestResponse(
        accepted=count,
        batch_id=batch.batch_id,
        station_id=station_id,
    )
