"""Async SQLAlchemy engine and session factory for VajraX services.

Supports both Neon serverless PostgreSQL (cloud) and local PostgreSQL (edge).
All connections go through asyncpg. SSL is enforced automatically for Neon
hosts (*.neon.tech) via connect_args, not query-string sslmode (asyncpg
doesn't support the latter).

Usage:
    from shared.db.async_base import get_async_engine, get_async_session

    engine = get_async_engine(database_url)
    async with get_async_session(engine) as session:
        result = await session.execute(select(SensorReading))
"""
from __future__ import annotations

import os
import re
import ssl
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _normalise_url(url: str) -> tuple[str, dict]:
    """Normalise a database URL for asyncpg and return (url, connect_args).

    - Converts ``postgresql://`` / ``postgres://`` to ``postgresql+asyncpg://``.
    - For Neon endpoints, strips ``sslmode`` / ``channel_binding`` query params
      (asyncpg ignores them) and instead returns ``ssl=<ctx>`` in connect_args.
    """
    # Driver prefix
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    connect_args: dict = {}

    if "neon.tech" in url:
        # Strip query params that asyncpg doesn't understand
        url = re.sub(r"[?&]sslmode=[^&]*", "", url)
        url = re.sub(r"[?&]channel_binding=[^&]*", "", url)
        url = re.sub(r"[?&]+$", "", url)  # clean up trailing ? or &

        # Inject SSL via connect_args (the correct asyncpg way)
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        connect_args["ssl"] = ctx

    return url, connect_args


def get_async_engine(
    database_url: str | None = None,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine optimised for Neon / standard PG.

    Connection pool is intentionally kept small because Neon serverless has
    per-branch connection limits (typically 100 total across all clients).
    """
    raw_url = database_url or os.environ.get("CLOUD_DATABASE_URL") or os.environ["DATABASE_URL"]
    url, connect_args = _normalise_url(raw_url)

    return create_async_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=connect_args,
        # Keep the pool conservative for Neon serverless
        pool_size=3,
        max_overflow=7,
        # Neon suspends compute after 5 min of inactivity; recycle connections
        # before the server-side idle timeout (600 s default).
        pool_recycle=300,
    )


def get_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a bound async session factory for the given engine."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def get_async_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a DB session and handles commit/rollback."""
    factory = get_async_session_factory(engine)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
