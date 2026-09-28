"""FastAPI dependency providers for Cloud services."""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.async_base import get_async_session

_engine = None


def set_engine(engine) -> None:
    global _engine
    _engine = engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session(_engine) as session:
        yield session
