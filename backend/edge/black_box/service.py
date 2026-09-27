"""Edge Black-Box Logger — tamper-evident critical event recorder.

Activated when a CRITICAL alert is raised. Records all sensor readings
into an append-only, SHA-256 hash-chained frame sequence. The chain anchors
to the triggering alert ID, providing end-to-end tamper evidence.

Window lifecycle:
  PRE_EVENT   — 5 min of readings before the trigger (queried from DB on activation)
  ACTIVE      — live readings from trigger time until alert is resolved
  POST_RESOLUTION — 15 min of readings after alert resolution, then window closes

Each frame = JSON-serialised list of sensor readings for a time slice.
Frame hashes are computed on the raw bytes to detect modification.

The logger subscribes to Redis alerts:{station_id} channel for CRITICAL
alert events and resolution events from the AlertEngine.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.crypto.hash_chain import compute_frame_hash, initial_prev_hash
from shared.db.models.edge import Alert, BlackBoxFrame, SensorReading
from shared.utils.time import utcnow
from edge.redis_client import alerts_channel, get_redis

log = structlog.get_logger(__name__)

# Phase constants stored in DB
PHASE_PRE_EVENT = "PRE_EVENT"
PHASE_ACTIVE = "ACTIVE"
PHASE_POST_RESOLUTION = "POST_RESOLUTION"


class ActiveWindow:
    """Tracks state of one open black-box event window."""

    def __init__(
        self,
        event_id: str,
        trigger_alert_id: str,
        station_id: str,
        triggered_at: datetime,
    ) -> None:
        self.event_id = event_id
        self.trigger_alert_id = trigger_alert_id
        self.station_id = station_id
        self.triggered_at = triggered_at
        self.frame_index: int = 0
        self.prev_hash: bytes = initial_prev_hash(trigger_alert_id)
        self.phase: str = PHASE_ACTIVE
        self.resolved_at: Optional[datetime] = None
        self.close_at: Optional[datetime] = None  # set when resolution detected


class BlackBoxLogger:
    """Background service: records tamper-evident black-box frames for CRITICAL events."""

    def __init__(
        self,
        station_id: str,
        session_factory: async_sessionmaker[AsyncSession],
        pre_event_s: int = 300,
        post_resolution_s: int = 900,
        frame_interval_s: int = 10,
    ) -> None:
        self._station_id = station_id
        self._session_factory = session_factory
        self._pre_event_s = pre_event_s
        self._post_resolution_s = post_resolution_s
        self._frame_interval_s = frame_interval_s
        self._windows: Dict[str, ActiveWindow] = {}  # event_id → window
        self._tasks: Dict[str, asyncio.Task] = {}    # event_id → frame writer task
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the alert listener and resume any open windows from DB."""
        self._running = True
        await self._resume_open_windows()
        self._listener_task = asyncio.create_task(
            self._listen_for_alerts(), name="blackbox-listener"
        )
        log.info("edge.blackbox.started", station_id=self._station_id)

    async def stop(self) -> None:
        """Stop all frame writers and the alert listener."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()
        log.info("edge.blackbox.stopped", station_id=self._station_id)

    # ---------------------------------------------------------------------------
    # Alert listener
    # ---------------------------------------------------------------------------

    async def _listen_for_alerts(self) -> None:
        """Subscribe to alerts channel and dispatch new CRITICAL events."""
        redis = get_redis()
        pubsub = redis.pubsub()
        channel = alerts_channel(self._station_id)
        await pubsub.subscribe(channel)
        log.info("edge.blackbox.subscribed", channel=channel)

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                try:
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    payload = json.loads(data)
                    await self._on_alert_event(payload)
                except Exception as exc:
                    log.error("edge.blackbox.listen_error", error=str(exc))
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def _on_alert_event(self, payload: Dict[str, Any]) -> None:
        """Dispatch an alert event to the appropriate handler."""
        severity = payload.get("severity", "")
        ack_state = payload.get("ack_state", "")
        alert_id = payload.get("alert_id", "")

        if severity == "CRITICAL" and ack_state == "OPEN":
            await self._activate_window(payload)
        elif ack_state == "RESOLVED":
            await self._on_alert_resolved(alert_id)

    # ---------------------------------------------------------------------------
    # Window lifecycle
    # ---------------------------------------------------------------------------

    async def _activate_window(self, alert_payload: Dict[str, Any]) -> None:
        """Open a new black-box window for a CRITICAL alert."""
        alert_id = alert_payload["alert_id"]
        triggered_at_str = alert_payload.get("triggered_at", utcnow().isoformat())
        triggered_at = datetime.fromisoformat(
            triggered_at_str.replace("Z", "+00:00")
        )
        event_id = f"bb-{self._station_id}-{str(uuid.uuid4())[:8]}"

        log.warning(
            "edge.blackbox.window_activated",
            event_id=event_id,
            alert_id=alert_id,
            station_id=self._station_id,
        )

        window = ActiveWindow(
            event_id=event_id,
            trigger_alert_id=alert_id,
            station_id=self._station_id,
            triggered_at=triggered_at,
        )
        self._windows[event_id] = window

        # Mark the triggering alert as having black_box_activated=True
        async with self._session_factory() as session:
            result = await session.execute(
                select(Alert).where(Alert.alert_id == alert_id)
            )
            alert = result.scalar_one_or_none()
            if alert:
                alert.black_box_activated = True
            await session.commit()

            # Write pre-event frames
            await self._write_pre_event_frames(window, session)

        # Start the continuous frame writer task
        task = asyncio.create_task(
            self._frame_writer_loop(window),
            name=f"blackbox-writer-{event_id}",
        )
        self._tasks[event_id] = task

    async def _on_alert_resolved(self, alert_id: str) -> None:
        """Begin post-resolution countdown for windows tied to this alert."""
        now = utcnow()
        for window in self._windows.values():
            if window.trigger_alert_id == alert_id and window.phase == PHASE_ACTIVE:
                window.phase = PHASE_POST_RESOLUTION
                window.resolved_at = now
                window.close_at = now + timedelta(seconds=self._post_resolution_s)
                log.info(
                    "edge.blackbox.post_resolution_started",
                    event_id=window.event_id,
                    close_at=window.close_at.isoformat(),
                )

    # ---------------------------------------------------------------------------
    # Frame writing
    # ---------------------------------------------------------------------------

    async def _write_pre_event_frames(
        self, window: ActiveWindow, session: AsyncSession
    ) -> None:
        """Query the last pre_event_s of readings and write as PRE_EVENT frames."""
        cutoff = window.triggered_at - timedelta(seconds=self._pre_event_s)
        result = await session.execute(
            select(SensorReading)
            .where(SensorReading.station_id == self._station_id)
            .where(SensorReading.timestamp_utc >= cutoff)
            .where(SensorReading.timestamp_utc < window.triggered_at)
            .order_by(SensorReading.timestamp_utc)
        )
        readings = result.scalars().all()

        if not readings:
            log.info(
                "edge.blackbox.no_pre_event_data",
                event_id=window.event_id,
                cutoff=cutoff.isoformat(),
            )
            return

        # Bucket into frame_interval_s slices
        buckets: Dict[int, List[Any]] = {}
        for r in readings:
            ts = r.timestamp_utc
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            bucket_key = int(ts.timestamp()) // self._frame_interval_s
            buckets.setdefault(bucket_key, []).append(r)

        for bucket_key in sorted(buckets.keys()):
            bucket_readings = buckets[bucket_key]
            ts = bucket_readings[0].timestamp_utc
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            await self._write_frame(
                window=window,
                readings=bucket_readings,
                timestamp_utc=ts,
                phase=PHASE_PRE_EVENT,
                session=session,
                is_partial=True,
            )

    async def _frame_writer_loop(self, window: ActiveWindow) -> None:
        """Write one frame every frame_interval_s seconds until window closes."""
        while self._running:
            await asyncio.sleep(self._frame_interval_s)

            now = utcnow()
            # Check if post-resolution countdown expired
            if window.close_at is not None and now >= window.close_at:
                await self._close_window(window)
                break

            # Query the most recent readings (last frame_interval_s seconds)
            cutoff = now - timedelta(seconds=self._frame_interval_s)
            async with self._session_factory() as session:
                result = await session.execute(
                    select(SensorReading)
                    .where(SensorReading.station_id == self._station_id)
                    .where(SensorReading.timestamp_utc >= cutoff)
                    .where(SensorReading.timestamp_utc <= now)
                    .order_by(SensorReading.timestamp_utc)
                )
                readings = result.scalars().all()
                await self._write_frame(
                    window=window,
                    readings=readings,
                    timestamp_utc=now,
                    phase=window.phase,
                    session=session,
                )
                await session.commit()

    async def _close_window(self, window: ActiveWindow) -> None:
        """Write the final frame with window_closed=True and remove the window."""
        async with self._session_factory() as session:
            await self._write_frame(
                window=window,
                readings=[],
                timestamp_utc=utcnow(),
                phase=PHASE_POST_RESOLUTION,
                session=session,
                window_closed=True,
            )
            await session.commit()

        del self._windows[window.event_id]
        if window.event_id in self._tasks:
            del self._tasks[window.event_id]

        log.info(
            "edge.blackbox.window_closed",
            event_id=window.event_id,
            total_frames=window.frame_index,
        )

    async def _write_frame(
        self,
        window: ActiveWindow,
        readings: List[Any],
        timestamp_utc: datetime,
        phase: str,
        session: AsyncSession,
        is_partial: bool = False,
        window_closed: bool = False,
    ) -> None:
        """Serialize readings, hash, and insert one BlackBoxFrame row."""
        # Serialize readings as JSON bytes (proto bindings come in Phase 3)
        readings_data = [
            {
                "sensor_id": r.sensor_id,
                "value": r.value,
                "unit": r.unit,
                "quality": r.quality,
                "timestamp_utc": r.timestamp_utc.isoformat()
                    if hasattr(r, "timestamp_utc") else "",
            }
            for r in readings
        ] if readings else []
        payload_bytes = json.dumps(readings_data).encode("utf-8")

        # Compute hash chain
        frame_hash = compute_frame_hash(payload_bytes)
        prev_hash = window.prev_hash

        frame = BlackBoxFrame(
            frame_id=str(uuid.uuid4()),
            event_id=window.event_id,
            station_id=self._station_id,
            trigger_alert_id=window.trigger_alert_id,
            frame_index=window.frame_index,
            readings_protobuf=payload_bytes,
            phase=phase,
            prev_hash=prev_hash,
            frame_hash=frame_hash,
            timestamp_utc=timestamp_utc,
            is_partial_pre_event=is_partial,
            window_closed=window_closed,
            synced_to_cloud=False,
        )
        session.add(frame)

        # Advance chain
        window.prev_hash = frame_hash
        window.frame_index += 1

    async def _resume_open_windows(self) -> None:
        """On service restart: resume any windows that were open in the DB."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(BlackBoxFrame)
                .where(BlackBoxFrame.station_id == self._station_id)
                .where(BlackBoxFrame.window_closed == False)  # noqa: E712
                .order_by(BlackBoxFrame.event_id, BlackBoxFrame.frame_index.desc())
                .distinct(BlackBoxFrame.event_id)
            )
            last_frames = result.scalars().all()

        for frame in last_frames:
            log.warning(
                "edge.blackbox.resuming_window",
                event_id=frame.event_id,
                last_frame_index=frame.frame_index,
            )
            window = ActiveWindow(
                event_id=frame.event_id,
                trigger_alert_id=frame.trigger_alert_id,
                station_id=self._station_id,
                triggered_at=frame.timestamp_utc,
            )
            window.frame_index = frame.frame_index + 1
            window.prev_hash = bytes(frame.frame_hash)
            window.phase = PHASE_ACTIVE
            self._windows[frame.event_id] = window
            task = asyncio.create_task(
                self._frame_writer_loop(window),
                name=f"blackbox-writer-{frame.event_id}",
            )
            self._tasks[frame.event_id] = task
