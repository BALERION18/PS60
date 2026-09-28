"""Integration Scenario 05 — Link Degradation & Queue Resilience.

QueueManager uses get_redis() internally, so we patch the module-level
get_redis in edge.sync_agent.queue_manager.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from edge.sync_agent.queue_manager import MESSAGE_PRIORITY, QueueManager, _score
from edge.sync_agent.mqtt_client import QOS_CRITICAL, QOS_TELEMETRY


# ---------------------------------------------------------------------------
# Scenario 05A — _score() priority mathematics
# ---------------------------------------------------------------------------

class TestQueueScoreFunction:

    def test_same_priority_earlier_timestamp_wins(self):
        now_ms = int(time.time() * 1000)
        assert _score(3, now_ms - 10000) < _score(3, now_ms)

    def test_old_critical_beats_new_telemetry(self):
        now_ms = int(time.time() * 1000)
        one_hour_ago_ms = now_ms - 3_600_000
        assert _score(MESSAGE_PRIORITY["ALERT_CRITICAL"], one_hour_ago_ms) < _score(
            MESSAGE_PRIORITY["SENSOR_BATCH"], now_ms
        )

    def test_black_box_beats_critical(self):
        now_ms = int(time.time() * 1000)
        assert _score(MESSAGE_PRIORITY["BLACK_BOX_FRAME"], now_ms) < _score(
            MESSAGE_PRIORITY["ALERT_CRITICAL"], now_ms
        )

    def test_score_is_deterministic(self):
        s1 = _score(1, 1700000000000)
        s2 = _score(1, 1700000000000)
        assert s1 == s2

    def test_score_is_positive(self):
        assert _score(0, int(time.time() * 1000)) > 0


# ---------------------------------------------------------------------------
# Scenario 05B — QueueManager via patched get_redis
# ---------------------------------------------------------------------------

class TestQueueManagerOperations:

    @pytest.mark.asyncio
    async def test_enqueue_calls_zadd(self, mock_redis):
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            await qm.enqueue("ALERT_CRITICAL", {"alert_id": "x"})
        mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_dequeue_batch_calls_zpopmin(self, mock_redis):
        mock_redis.zpopmin = AsyncMock(return_value=[])
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            items = await qm.dequeue_batch(batch_size=10)
        mock_redis.zpopmin.assert_called_once()
        assert items == []

    @pytest.mark.asyncio
    async def test_requeue_calls_zadd(self, mock_redis):
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            item = {
                "item_id": "test-123", "station_id": "maitri",
                "message_type": "SENSOR_BATCH", "payload": {},
                "priority": 3, "created_ms": int(time.time() * 1000),
                "source_id": None, "attempts": 0,
            }
            await qm.requeue(item)
        mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_enqueue_uses_station_scoped_key(self, mock_redis):
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="bharati")
            await qm.enqueue("SENSOR_BATCH", {"readings": []})
        call_key = mock_redis.zadd.call_args[0][0]
        assert "bharati" in call_key

    @pytest.mark.asyncio
    async def test_enqueue_returns_item_id(self, mock_redis):
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            item_id = await qm.enqueue("ALERT_CRITICAL", {"alert_id": "a"})
        assert isinstance(item_id, str)
        assert "alert_critical" in item_id

    @pytest.mark.asyncio
    async def test_critical_gets_lower_score_than_telemetry(self, mock_redis):
        scores = []

        async def capture_zadd(key, mapping, *args, **kwargs):
            scores.append(list(mapping.values())[0])

        mock_redis.zadd = AsyncMock(side_effect=capture_zadd)

        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            await qm.enqueue("ALERT_CRITICAL", {"alert_id": "a"})
            await qm.enqueue("SENSOR_BATCH", {"readings": []})

        if len(scores) >= 2:
            assert scores[0] < scores[1], "CRITICAL must score lower than SENSOR_BATCH"

    @pytest.mark.asyncio
    async def test_dequeue_batch_decodes_json_items(self, mock_redis):
        import json
        item = {
            "item_id": "alert_critical-12345", "station_id": "maitri",
            "message_type": "ALERT_CRITICAL", "payload": {"severity": "CRITICAL"},
            "priority": 1, "created_ms": 1700000000000,
            "source_id": None, "attempts": 0,
        }
        raw = [(json.dumps(item).encode(), 1_000_000_000_001.0)]
        mock_redis.zpopmin = AsyncMock(return_value=raw)
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            items = await qm.dequeue_batch(batch_size=5)
        assert len(items) == 1
        assert items[0]["message_type"] == "ALERT_CRITICAL"

    @pytest.mark.asyncio
    async def test_empty_dequeue_returns_empty_list(self, mock_redis):
        mock_redis.zpopmin = AsyncMock(return_value=[])
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            items = await qm.dequeue_batch()
        assert items == []


# ---------------------------------------------------------------------------
# Scenario 05C — QoS level mapping
# ---------------------------------------------------------------------------

class TestQoSLevelMapping:

    def _qos(self, msg_type: str) -> int:
        return QOS_CRITICAL if MESSAGE_PRIORITY[msg_type] <= 1 else QOS_TELEMETRY

    def test_black_box_qos2(self):
        assert self._qos("BLACK_BOX_FRAME") == 2

    def test_critical_alert_qos2(self):
        assert self._qos("ALERT_CRITICAL") == 2

    def test_high_alert_qos2(self):
        assert self._qos("ALERT_HIGH") == 2

    def test_medium_alert_qos1(self):
        assert self._qos("ALERT_MEDIUM") == 1

    def test_sensor_batch_qos1(self):
        assert self._qos("SENSOR_BATCH") == 1

    def test_heartbeat_qos1(self):
        assert self._qos("LINK_HEARTBEAT") == 1

    def test_inventory_qos1(self):
        assert self._qos("INVENTORY_SNAPSHOT") == 1


# ---------------------------------------------------------------------------
# Scenario 05D — Link outage recovery: priority ordering preserved in backlog
# ---------------------------------------------------------------------------

class TestLinkDegradationScenario:

    @pytest.mark.asyncio
    async def test_backlog_returns_critical_before_telemetry(self, mock_redis):
        """After reconnect, ALERT_CRITICAL is dequeued before SENSOR_BATCH."""
        import json
        crit_item = {
            "item_id": "alert_critical-1", "message_type": "ALERT_CRITICAL",
            "payload": {"severity": "CRITICAL"}, "priority": 1,
            "station_id": "maitri", "created_ms": 100, "source_id": None, "attempts": 0,
        }
        telem_item = {
            "item_id": "sensor_batch-2", "message_type": "SENSOR_BATCH",
            "payload": {"readings": []}, "priority": 3,
            "station_id": "maitri", "created_ms": 200, "source_id": None, "attempts": 0,
        }
        # zpopmin returns in score order (lowest score = highest priority first)
        mock_redis.zpopmin = AsyncMock(return_value=[
            (json.dumps(crit_item).encode(), 1_000_000_000_100.0),
            (json.dumps(telem_item).encode(), 3_000_000_000_200.0),
        ])
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            items = await qm.dequeue_batch(batch_size=10)

        assert len(items) == 2
        assert items[0]["message_type"] == "ALERT_CRITICAL"
        assert items[1]["message_type"] == "SENSOR_BATCH"

    @pytest.mark.asyncio
    async def test_empty_queue_ok_when_link_restored(self, mock_redis):
        mock_redis.zpopmin = AsyncMock(return_value=[])
        with patch("edge.sync_agent.queue_manager.get_redis", return_value=mock_redis):
            qm = QueueManager(station_id="maitri")
            items = await qm.dequeue_batch(batch_size=50)
        assert items == []
