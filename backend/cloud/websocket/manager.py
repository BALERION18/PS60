"""WebSocket connection manager for real-time HQ dashboard push.

Maintains a dict of connected WebSocket clients. When a new alert or
station status change arrives on the Redis pub/sub channel, it is
broadcast to all connected HQ dashboard clients immediately.

Usage:
  manager = WebSocketManager()
  await manager.connect(websocket, client_id)
  await manager.broadcast({"type": "alert", "data": alert_dict})
  manager.disconnect(client_id)

The background Redis subscriber task is started by the app lifespan
and runs for the duration of the process.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

import structlog
from fastapi import WebSocket

from cloud.redis_client import cloud_alerts_channel, get_redis, station_status_channel

log = structlog.get_logger(__name__)


class WebSocketManager:
    """Manages connected HQ dashboard WebSocket clients."""

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._redis_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self._connections[client_id] = websocket
        log.info("cloud.ws.connected", client_id=client_id, total=len(self._connections))

    def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        log.info("cloud.ws.disconnected", client_id=client_id, total=len(self._connections))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send a JSON message to all connected clients. Drops stale connections."""
        if not self._connections:
            return
        payload = json.dumps(message, default=str)
        dead: list[str] = []
        for client_id, ws in list(self._connections.items()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(client_id)
        for cid in dead:
            self.disconnect(cid)

    async def start_redis_listener(self) -> None:
        """Start background task that broadcasts Redis pub/sub events to WebSocket clients."""
        self._redis_task = asyncio.create_task(
            self._listen_redis(), name="ws-redis-listener"
        )

    async def stop(self) -> None:
        if self._redis_task and not self._redis_task.done():
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass

    async def _listen_redis(self) -> None:
        """Subscribe to cloud alert and station-status channels → broadcast to WS."""
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(cloud_alerts_channel())
        # Subscribe to all stations' status channels
        from cloud.config import get_config
        cfg = get_config()
        for sid in cfg.station_ids:
            await pubsub.subscribe(station_status_channel(sid))

        log.info("cloud.ws.redis_listener.started")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    channel = message.get("channel")
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")

                    payload = json.loads(data)
                    # Tag message with its type for the frontend
                    if "alert_id" in payload:
                        envelope = {"type": "alert", "data": payload}
                    else:
                        envelope = {"type": "station_status", "data": payload}
                    await self.broadcast(envelope)
                except Exception as exc:
                    log.error("cloud.ws.broadcast_error", error=str(exc))
        finally:
            await pubsub.aclose()
