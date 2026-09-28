"""Outbound queue manager — Redis sorted set for Edge→Cloud satellite queue.

Queue structure:
  Key:   queue:outbound:{station_id}          (Redis sorted set)
  Score: priority * 1_000_000_000_000 + created_at_unix_ms
  Value: JSON-serialised QueueItem dict

Lower score = dequeued first.
  Priority 0 (black_box)      — never evicted, always first
  Priority 1 (CRITICAL/HIGH alerts) — high urgency
  Priority 2 (MEDIUM/LOW alerts, heartbeat, ack)
  Priority 3 (telemetry sensor batches) — best-effort, evicted first

Overflow eviction: when the queue exceeds max_bytes, priority-3 items
are removed from the tail (highest score) first.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from edge.redis_client import get_redis, queue_key
from shared.utils.time import unix_ms, utcnow

log = structlog.get_logger(__name__)

# Priority map: MQTT message_type string → queue priority
MESSAGE_PRIORITY: Dict[str, int] = {
    "BLACK_BOX_FRAME":      0,
    "ALERT_CRITICAL":       1,
    "ALERT_HIGH":           1,
    "ALERT_MEDIUM":         2,
    "ALERT_LOW":            2,
    "ALERT_ACK":            2,
    "LINK_HEARTBEAT":       2,
    "INVENTORY_SNAPSHOT":   3,
    "SENSOR_BATCH":         3,
}


def _score(priority: int, created_ms: int) -> float:
    """Sorted-set score: lower = dequeue first."""
    return float(priority * 1_000_000_000_000 + created_ms)


class QueueManager:
    """Manages the Redis outbound sorted-set queue for one station."""

    def __init__(
        self,
        station_id: str,
        max_bytes: int = 512 * 1024 * 1024,  # 512 MB default
    ) -> None:
        self._station_id = station_id
        self._max_bytes = max_bytes
        self._key = queue_key(station_id)

    async def enqueue(
        self,
        message_type: str,
        payload: Dict[str, Any],
        priority: Optional[int] = None,
        source_id: Optional[str] = None,
    ) -> str:
        """Add one item to the outbound queue.

        Returns:
            The generated item_id for tracking.
        """
        redis = get_redis()
        p = priority if priority is not None else MESSAGE_PRIORITY.get(message_type, 3)
        now_ms = unix_ms(utcnow())
        item_id = f"{message_type.lower()}-{now_ms}"

        item: Dict[str, Any] = {
            "item_id": item_id,
            "station_id": self._station_id,
            "message_type": message_type,
            "payload": payload,
            "priority": p,
            "created_ms": now_ms,
            "source_id": source_id,
            "attempts": 0,
        }
        value = json.dumps(item, default=str)
        score = _score(p, now_ms)
        await redis.zadd(self._key, {value: score})
        await self._maybe_evict()
        log.debug("edge.queue.enqueued", item_id=item_id, priority=p)
        return item_id

    async def dequeue_batch(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Atomically pop up to batch_size highest-priority items."""
        redis = get_redis()
        raw = await redis.zpopmin(self._key, count=batch_size)
        items: List[Dict[str, Any]] = []
        for value, _ in raw:
            try:
                decoded = value.decode() if isinstance(value, bytes) else value
                items.append(json.loads(decoded))
            except Exception as exc:
                log.error("edge.queue.decode_error", error=str(exc))
        return items

    async def requeue(self, item: Dict[str, Any]) -> None:
        """Re-add a failed item with incremented attempt counter and backoff."""
        redis = get_redis()
        item["attempts"] = item.get("attempts", 0) + 1
        # Exponential backoff: delay re-delivery by up to 5 min
        backoff_ms = min(item["attempts"] * 30_000, 300_000)
        score = _score(item["priority"], item["created_ms"] + backoff_ms)
        await redis.zadd(self._key, {json.dumps(item, default=str): score})

    async def queue_depth(self) -> int:
        """Number of items in queue."""
        return await get_redis().zcard(self._key)

    async def queue_size_bytes(self) -> int:
        """Approximate total queue size in bytes."""
        items = await get_redis().zrange(self._key, 0, -1)
        return sum(len(v) for v in items)

    async def _maybe_evict(self) -> None:
        """Evict lowest-priority items until queue is under max_bytes budget."""
        size = await self.queue_size_bytes()
        if size <= self._max_bytes:
            return
        redis = get_redis()
        evicted = 0
        while size > self._max_bytes:
            removed = await redis.zpopmax(self._key, count=1)
            if not removed:
                break
            evicted += 1
            size = await self.queue_size_bytes()
        if evicted:
            log.warning("edge.queue.evicted", station_id=self._station_id, count=evicted)
