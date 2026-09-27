"""Cloud MQTT subscriber — listens to all station sync topics and heartbeats.

Subscribes to:
  dt/+/sync/#        — all SyncEnvelopes from both stations
  dt/+/heartbeat     — link heartbeats from both stations

Topic parsing extracts station_id from the second segment:
  dt/{station_id}/sync/{message_type}  →  station_id = topic[1]
  dt/{station_id}/heartbeat            →  station_id = topic[1]

On each message: parses the JSON envelope, calls CloudIngestionService.receive_envelope().
Reconnects with exponential backoff on MQTT failure.
"""
from __future__ import annotations

import asyncio
import json
import ssl
from typing import TYPE_CHECKING, Optional

import structlog

# aiomqtt is only needed when MQTT is actually enabled.
# Import lazily so the app starts cleanly even when MQTT_ENABLED=false.
try:
    import aiomqtt
    _AIOMQTT_AVAILABLE = True
except ImportError:  # pragma: no cover
    aiomqtt = None          # type: ignore[assignment]
    _AIOMQTT_AVAILABLE = False

log = structlog.get_logger(__name__)


class CloudMQTTSubscriber:
    """Subscribes to all station topics and dispatches to ingestion service."""

    def __init__(
        self,
        host: str,
        port: int,
        ingestion_service,   # CloudIngestionService — avoid circular import
        tls: bool = False,
        ca_cert_path: Optional[str] = None,
        keepalive: int = 60,
    ) -> None:
        self._host = host
        self._port = port
        self._ingestion = ingestion_service
        self._tls = tls
        self._ca_cert = ca_cert_path
        self._keepalive = keepalive
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def _build_tls_context(self) -> Optional[ssl.SSLContext]:
        if not self._tls:
            return None
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if self._ca_cert:
            ctx.load_verify_locations(self._ca_cert)
        return ctx

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(
            self._run_with_reconnect(), name="cloud-mqtt-subscriber"
        )
        log.info("cloud.mqtt.subscriber.started", host=self._host, port=self._port)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("cloud.mqtt.subscriber.stopped")

    async def _run_with_reconnect(self) -> None:
        """Connect to broker, subscribe, process messages. Reconnect on failure."""
        backoff = 1
        tls_ctx = self._build_tls_context()

        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._port,
                    keepalive=self._keepalive,
                    identifier="vajrax-cloud-receiver",
                    tls_context=tls_ctx,
                ) as client:
                    backoff = 1
                    log.info("cloud.mqtt.connected", host=self._host, port=self._port)

                    # Subscribe to all station sync and heartbeat topics
                    await client.subscribe("dt/+/sync/#", qos=1)
                    await client.subscribe("dt/+/heartbeat", qos=1)

                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._dispatch(message)

            except aiomqtt.MqttError as exc:
                log.warning("cloud.mqtt.disconnected", error=str(exc), retry_in_s=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("cloud.mqtt.error", error=str(exc))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _dispatch(self, message: aiomqtt.Message) -> None:
        """Parse topic, extract station_id, dispatch to ingestion service."""
        topic_parts = str(message.topic).split("/")
        # dt/{station_id}/sync/{type}  OR  dt/{station_id}/heartbeat
        if len(topic_parts) < 3:
            return

        station_id = topic_parts[1]
        kind = topic_parts[2]  # "sync" or "heartbeat"

        try:
            raw = message.payload
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.error("cloud.mqtt.parse_error", topic=str(message.topic), error=str(exc))
            return

        # Normalise heartbeat to a LINK_HEARTBEAT envelope
        if kind == "heartbeat":
            envelope.setdefault("message_type", "LINK_HEARTBEAT")
            envelope.setdefault("station_id", station_id)

        try:
            await self._ingestion.receive_envelope(envelope, station_id)
        except Exception as exc:
            log.error(
                "cloud.mqtt.dispatch_error",
                station_id=station_id,
                error=str(exc),
            )
