"""FastAPI dependency providers for Edge services.

These are injected into route handlers via Depends().
They provide: DB session, station_id, Redis client.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.async_base import get_async_session
from edge.redis_client import get_redis

# These are populated during app startup lifespan
_engine = None
_station_id: str = ""


def set_engine(engine) -> None:
    global _engine
    _engine = engine


def set_station_id(sid: str) -> None:
    global _station_id
    _station_id = sid


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session per request."""
    async with get_async_session(_engine) as session:
        yield session


def get_station_id() -> str:
    """FastAPI dependency: return this Edge's station_id."""
    return _station_id
