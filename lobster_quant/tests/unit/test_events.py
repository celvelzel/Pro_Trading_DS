"""
Tests for EventBus and Event system.
"""

import pytest
from unittest.mock import MagicMock
from src.core.events import EventBus, Event, EventType, event_bus


class TestEventType:
    def test_event_types_exist(self):
        assert EventType.DATA_UPDATED is not None
        assert EventType.SIGNAL_GENERATED is not None
        assert EventType.OFF_FILTER_TRIGGERED is not None
        assert EventType.BACKTEST_COMPLETED is not None
        assert EventType.ERROR_OCCURRED is not None


class TestEvent:
    def test_create_event(self):
        event = Event(type=EventType.DATA_UPDATED, payload={"symbol": "AAPL"})
        assert event.type == EventType.DATA_UPDATED
        assert event.payload == {"symbol": "AAPL"}
        assert event.source == "unknown"

    def test_event_with_source(self):
        event = Event(type=EventType.SIGNAL_GENERATED, payload={}, source="test")
        assert event.source == "test"


def _make_handler(name: str = "handler") -> MagicMock:
    """Create a MagicMock handler with __name__ set for EventBus compatibility."""
    handler = MagicMock()
    handler.__name__ = name
    return handler


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        handler = _make_handler("test_handler")
        bus.subscribe(EventType.DATA_UPDATED, handler)
        event = Event(type=EventType.DATA_UPDATED, payload="test")
        bus.publish(event)
        handler.assert_called_once_with(event)

    def test_publish_no_subscribers(self):
        bus = EventBus()
        event = Event(type=EventType.DATA_UPDATED, payload="test")
        bus.publish(event)

    def test_multiple_subscribers(self):
        bus = EventBus()
        handler1 = _make_handler("handler1")
        handler2 = _make_handler("handler2")
        bus.subscribe(EventType.SIGNAL_GENERATED, handler1)
        bus.subscribe(EventType.SIGNAL_GENERATED, handler2)
        event = Event(type=EventType.SIGNAL_GENERATED, payload="test")
        bus.publish(event)
        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_unsubscribe(self):
        bus = EventBus()
        handler = _make_handler("test_handler")
        bus.subscribe(EventType.DATA_UPDATED, handler)
        bus.unsubscribe(EventType.DATA_UPDATED, handler)
        event = Event(type=EventType.DATA_UPDATED, payload="test")
        bus.publish(event)
        handler.assert_not_called()

    def test_handler_exception_does_not_stop_others(self):
        bus = EventBus()
        failing = MagicMock(side_effect=Exception("fail"))
        failing.__name__ = "failing_handler"
        success = _make_handler("success_handler")
        bus.subscribe(EventType.ERROR_OCCURRED, failing)
        bus.subscribe(EventType.ERROR_OCCURRED, success)
        event = Event(type=EventType.ERROR_OCCURRED, payload="test")
        bus.publish(event)
        success.assert_called_once()

    def test_clear_specific(self):
        bus = EventBus()
        handler = _make_handler("test_handler")
        bus.subscribe(EventType.DATA_UPDATED, handler)
        bus.subscribe(EventType.SIGNAL_GENERATED, handler)
        bus.clear(EventType.DATA_UPDATED)
        bus.publish(Event(type=EventType.DATA_UPDATED, payload="test"))
        bus.publish(Event(type=EventType.SIGNAL_GENERATED, payload="test"))
        assert handler.call_count == 1

    def test_clear_all(self):
        bus = EventBus()
        handler = _make_handler("test_handler")
        bus.subscribe(EventType.DATA_UPDATED, handler)
        bus.subscribe(EventType.SIGNAL_GENERATED, handler)
        bus.clear()
        bus.publish(Event(type=EventType.DATA_UPDATED, payload="test"))
        handler.assert_not_called()


class TestGlobalEventBus:
    def test_global_exists(self):
        assert isinstance(event_bus, EventBus)
