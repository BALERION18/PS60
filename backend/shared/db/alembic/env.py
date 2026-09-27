"""Alembic environment configuration for VajraX — Neon PostgreSQL targets.

Migration targets
-----------------
Set the ``MIGRATION_TARGET`` environment variable before running alembic:

    MIGRATION_TARGET=edge   → runs Edge schema against EDGE_DATABASE_URL
    MIGRATION_TARGET=cloud  → runs Cloud schema against CLOUD_DATABASE_URL (default)

Both targets use the same ORM Base so Alembic can diff the correct subset of
tables for each database.

Example
-------
    MIGRATION_TARGET=cloud  alembic -c shared/db/alembic.ini upgrade head
    MIGRATION_TARGET=edge   alembic -c shared/db/alembic.ini upgrade head
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Determine migration target (default: cloud)
# ---------------------------------------------------------------------------
target = os.environ.get("MIGRATION_TARGET", "cloud").lower()

# ---------------------------------------------------------------------------
# Import the correct set of models so metadata is fully populated
# ---------------------------------------------------------------------------
if target == "edge":
    # Edge DB — import only edge tables
    from shared.db.models.edge import (  # noqa: F401
        SensorReading,
        Alert,
        OutboundQueueItem,
        BlackBoxFrame,
        InventoryItem,
        AssetCache,
        AuditLogEntry,
        LinkStatusRecord,
    )
else:
    # Cloud DB — import all cloud models (which re-exports shared edge models)
    from shared.db.models.cloud import *  # noqa: F401, F403
    # Also register edge-only tables that the Cloud DB mirrors
    from shared.db.models.edge import OutboundQueueItem, AssetCache  # noqa: F401

from shared.db.base import Base

# ---------------------------------------------------------------------------
# Alembic config
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Inject the correct DATABASE_URL for the chosen migration target
# ---------------------------------------------------------------------------
def _get_sync_url() -> str:
    """Return a *synchronous* psycopg2-compatible URL for Alembic.

    Reads EDGE_DATABASE_URL or CLOUD_DATABASE_URL depending on the target,
    with a fallback to the generic DATABASE_URL env var.
    Strips asyncpg driver prefix so psycopg2 is used for the migration run.
    """
    if target == "edge":
        url = (
            os.environ.get("EDGE_DATABASE_URL")
            or os.environ.get("DATABASE_URL", "")
        )
    else:
        url = (
            os.environ.get("CLOUD_DATABASE_URL")
            or os.environ.get("DATABASE_URL", "")
        )

    if not url:
        raise RuntimeError(
            f"No database URL found for target '{target}'. "
            "Set EDGE_DATABASE_URL or CLOUD_DATABASE_URL in your environment."
        )

    # Convert async driver prefixes to their sync equivalents for Alembic
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres+asyncpg://", "postgresql://")

    return url


sync_url = _get_sync_url()
config.set_main_option("sqlalchemy.url", sync_url)


# ---------------------------------------------------------------------------
# Offline migration (generates SQL to stdout)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include only tables belonging to the current target branch
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (connects to Neon and runs DDL)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling during migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
