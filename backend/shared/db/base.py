"""SQLAlchemy engine factory and declarative base for VajraX."""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for all VajraX SQLAlchemy models."""
    pass


def get_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine from the given URL or the DATABASE_URL env var."""
    url = database_url or os.environ["DATABASE_URL"]
    engine = create_engine(url, echo=echo, future=True)
    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db(engine: Engine) -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session, close on exit."""
    SessionLocal = get_session_factory(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
