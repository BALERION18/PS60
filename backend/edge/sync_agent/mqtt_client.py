"""Async MQTT client wrapper for the Edge sync agent.

Wraps aiomqtt to provide:
  - Automatic reconnection with exponential backoff (1s → 60s)
  - Optional TLS / mTLS configuration
  - Topic-name helpers following the VajraX MQTT topic schema
  - Simple publish() and publish_heartbeat() coroutines

MQTT topic schema:
  Publish   → dt/{station_id}/sync/{message_type_lower}  (QoS 1 or 2)
  Publish   → dt/{station_id}/heartbeat                   (QoS 1)
  Subscribe ← cmd/{station_id}/#                          (downlink from Cloud)
"""
from __future__ import annotations

import asyncio
import ssl
from typing import Any, Callable, Coroutine, Optional

import aiomqtt
import structlog

log = structlog.get_logger(__name__)

# QoS levels
QOS_TELEMETRY = 1   # at-least-once for sensor batches and heartbeats
QOS_CRITICAL = 2    # exactly-once for CRITICAL alerts and black-box frames


# ---------------------------------------------------------------------------
# Topic helpers
# ---------------------------------------------------------------------------

def sync_topic(station_id: str, message_type: str) -> str:
    return f"dt/{station_id}/sync/{message_type.lower()}"


def heartbeat_topic(station_id: str) -> str:
    return f"dt/{station_id}/heartbeat"


def downlink_topic(station_id: str) -> str:
    return f"cmd/{station_id}/#"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class MQTTClient:
    """Manages MQTT connection lifecycle for the Edge sync agent."""

    def __init__(
        self,
        station_id: str,
        host: str,
        port: int,
        tls: bool = False,
        ca_cert_path: Optional[str] = None,
        client_cert_path: Optional[str] = None,
        client_key_path: Optional[str] = None,
        keepalive: int = 60,
    ) -> None:
        self._station_id = station_id
        self._host = host
        self._port = port
        self._tls = tls
        self._ca_cert = ca_cert_path
        self._client_cert = client_cert_path
        self._client_key = client_key_path
        self._keepalive = keepalive
        self._client: Optional[aiomqtt.Client] = None
        self._connected = False

    def _build_tls_context(self) -> Optional[ssl.SSLContext]:
        if not self._tls:
            return None
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if self._ca_cert:
            ctx.load_verify_locations(self._ca_cert)
        if self._client_cert and self._client_key:
            ctx.load_cert_chain(self._client_cert, self._client_key)
        return ctx

    async def publish(
        self,
        message_type: str,
        envelope_json: str,
        qos: int = QOS_TELEMETRY,
    ) -> None:
        """Publish a SyncEnvelope JSON string on the appropriate topic."""
        if self._client is None:
            raise RuntimeError("MQTT client not connected — cannot publish")
        topic = sync_topic(self._station_id, message_type)
        await self._client.publish(topic, payload=envelope_json.encode("utf-8"), qos=qos)
        log.debug("edge.mqtt.published", topic=topic, size=len(envelope_json), qos=qos)

    async def publish_heartbeat(self, payload: str) -> None:
        """Publish a heartbeat message."""
        if self._client is None:
            raise RuntimeError("MQTT client not connected — cannot publish heartbeat")
        topic = heartbeat_topic(self._station_id)
        await self._client.publish(topic, payload=payload.encode("utf-8"), qos=QOS_TELEMETRY)

    async def run_with_reconnect(
        self,
        on_connected: Callable[[], Coroutine],
    ) -> None:
        """Connect to broker, call on_connected(), reconnect on any error.

        Reconnection uses exponential backoff (1 → 2 → 4 … → 60 seconds).
        """
        backoff = 1
        tls_ctx = self._build_tls_context()
        client_id = f"vajrax-edge-{self._station_id}"

        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._port,
                    keepalive=self._keepalive,
                    identifier=client_id,
                    tls_context=tls_ctx,
                ) as client:
                    self._client = client
                    self._connected = True
                    backoff = 1
                    log.info(
                        "edge.mqtt.connected",
                        host=self._host,
                        port=self._port,
                        station_id=self._station_id,
                    )
                    await client.subscribe(downlink_topic(self._station_id), qos=QOS_TELEMETRY)
                    await on_connected()
            except aiomqtt.MqttError as exc:
                self._connected = False
                self._client = None
                log.warning("edge.mqtt.disconnected", error=str(exc), retry_in_s=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except asyncio.CancelledError:
                self._connected = False
                self._client = None
                break

    @property
    def is_connected(self) -> bool:
        return self._connected
