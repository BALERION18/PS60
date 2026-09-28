"""WebSocket endpoint — real-time HQ dashboard live feed."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import structlog

log = structlog.get_logger(__name__)
router = APIRouter(tags=["websocket"])

# Set at app startup by cloud/main.py
_manager = None


def set_manager(manager) -> None:
    global _manager
    _manager = manager


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time HQ dashboard updates.

    Streams JSON messages of two types:
      {"type": "alert",          "data": {alert fields…}}
      {"type": "station_status", "data": {station_id, link_state, last_heartbeat_at, …}}

    Clients should reconnect automatically on disconnect.
    """
    if _manager is None:
        await websocket.close(code=1011)
        return
    client_id = str(uuid.uuid4())[:8]
    await _manager.connect(websocket, client_id)
    try:
        # Keep connection open — we only push, never receive commands here
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _manager.disconnect(client_id)
    except Exception as exc:
        log.error("cloud.ws.endpoint_error", client_id=client_id, error=str(exc))
        _manager.disconnect(client_id)
