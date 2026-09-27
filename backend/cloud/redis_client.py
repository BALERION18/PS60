"""Cloud Redis client — async pool with channel name helpers.

Falls back to an in-memory dict-based mock when Redis is unavailable,
so the API (including auth) works in local dev without Docker.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger(__name__)

_pool: Optional[aioredis.Redis] = None
_mock: Optional["_MockRedis"] = None


class _MockRedis:
    """Minimal in-memory Redis mock for local dev without a real Redis server.

    Supports: get, set, setex, delete, publish (no-op).
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, float]] = {}  # key → (value, expires_at)
        self._lock = asyncio.Lock()

    def _clean(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp > 0 and now > exp]
        for k in expired:
            del self._store[k]

    async def get(self, key: str) -> Optional[bytes]:
        async with self._lock:
            self._clean()
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at > 0 and time.time() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: bytes | str) -> None:
        if isinstance(value, str):
            value = value.encode()
        async with self._lock:
            self._store[key] = (value, 0)

    async def setex(self, key: str, ttl_seconds: int, value: bytes | str) -> None:
        if isinstance(value, str):
            value = value.encode()
        async with self._lock:
            self._store[key] = (value, time.time() + ttl_seconds)

    async def delete(self, *keys: str) -> int:
        async with self._lock:
            count = 0
            for k in keys:
                if k in self._store:
                    del self._store[k]
                    count += 1
            return count

    async def ping(self) -> bool:
        return True

    async def publish(self, channel: str, message: str) -> None:
        pass  # No-op in mock

    async def aclose(self) -> None:
        pass

    async def pubsub(self):  # type: ignore[return]
        return _MockPubSub()


class _MockPubSub:
    async def subscribe(self, *args: str) -> None:
        pass

    async def listen(self):  # type: ignore[return]
        # Never yields — WebSocket live feed just stays empty in mock mode
        while True:
            await asyncio.sleep(3600)

    async def aclose(self) -> None:
        pass


async def init_redis(url: str) -> aioredis.Redis:
    global _pool
    client = aioredis.from_url(
        url,
        encoding="utf-8",
        decode_responses=False,
        socket_keepalive=True,
        health_check_interval=30,
    )
    await client.ping()   # Raises on connection failure
    _pool = client
    log.info("cloud.redis.connected", url=url)
    return _pool


async def init_mock_redis() -> "_MockRedis":
    """Initialise the in-memory mock. Called when real Redis is unavailable."""
    global _mock
    _mock = _MockRedis()
    log.warning("cloud.redis.using_mock",
                hint="No Redis — refresh tokens are in-memory only (not shared across restarts)")
    return _mock


async def close_redis() -> None:
    global _pool, _mock
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        log.info("cloud.redis.closed")
    _mock = None


def get_redis():
    """Return the active Redis client (real or mock)."""
    global _mock
    if _pool is not None:
        return _pool
    if _mock is not None:
        return _mock
    # Auto-initialise mock synchronously (safe during request handling)
    _mock = _MockRedis()
    log.warning("cloud.redis.auto_mock", reason="get_redis called before init")
    return _mock


# ---------------------------------------------------------------------------
# Channel name helpers
# ---------------------------------------------------------------------------

def cloud_alerts_channel() -> str:
    """Pub/sub channel for new alerts arriving from any station."""
    return "cloud:alerts:all"


def station_status_channel(station_id: str) -> str:
    """Pub/sub channel for station connection status updates."""
    return f"cloud:station:{station_id}:status"
