"""Time utilities for VajraX — all timestamps in UTC, always.

Every timestamp in VajraX is stored, transmitted, and compared in UTC.
These helpers enforce that invariant at the boundary between application
code and the outside world.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    Always use this instead of datetime.utcnow() (which returns a naive datetime).
    """
    return datetime.now(tz=timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is UTC-aware; raise if it has a non-UTC timezone."""
    if dt.tzinfo is None:
        raise ValueError(
            f"Received a naive datetime ({dt!r}). "
            "All VajraX datetimes must be timezone-aware UTC. "
            "Use shared.utils.time.utcnow() to create timestamps."
        )
    return dt.astimezone(timezone.utc)


def unix_ms(dt: datetime | None = None) -> int:
    """Return the Unix timestamp in milliseconds for the given (or current) UTC time."""
    if dt is None:
        dt = utcnow()
    return int(ensure_utc(dt).timestamp() * 1000)


def from_unix_ms(ms: int) -> datetime:
    """Convert a Unix millisecond timestamp to a UTC-aware datetime."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def iso_utc(dt: datetime | None = None) -> str:
    """Format a UTC datetime as an ISO 8601 string with Z suffix.

    Example: '2026-08-27T09:44:00.000Z'
    """
    if dt is None:
        dt = utcnow()
    return ensure_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
