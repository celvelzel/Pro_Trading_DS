"""
Lobster Quant - Event System
Lightweight publish-subscribe event bus for module decoupling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Optional

from ..utils.logging import get_logger

logger = get_logger()


class EventType(Enum):
    """Event types in the Lobster Quant system."""

    DATA_UPDATED = auto()
    SIGNAL_GENERATED = auto()
    OFF_FILTER_TRIGGERED = auto()
    BACKTEST_COMPLETED = auto()
    ERROR_OCCURRED = auto()


@dataclass
class Event:
    """An event in the system.

    Attributes:
        type: The event type.
        payload: Arbitrary event data.
        timestamp: When the event was created.
        source: Module or component that emitted the event.
    """

    type: EventType
    payload: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"


class EventBus:
    """Lightweight publish-subscribe event bus.

    Usage:
        bus = EventBus()

        def on_signal(event: Event):
            print(f"Signal: {event.payload}")

        bus.subscribe(EventType.SIGNAL_GENERATED, on_signal)
        bus.publish(Event(EventType.SIGNAL_GENERATED, {"symbol": "AAPL"}, source="signal_engine"))
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = {}

    def subscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: Event type to listen for.
            handler: Callable that takes an Event instance.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type.name}: {handler.__name__}")

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Each handler is called in registration order. Exceptions in one
        handler do not prevent other handlers from executing.

        Args:
            event: Event to publish.
        """
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.debug(f"No subscribers for {event.type.name}")
            return

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.error(
                    f"Event handler '{handler.__name__}' failed for "
                    f"{event.type.name}",
                    exc_info=True,
                )

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Remove a handler subscription.

        Args:
            event_type: Event type to unsubscribe from.
            handler: Handler to remove. Does nothing if not subscribed.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed from {event_type.name}: {handler.__name__}")

    def clear(self, event_type: Optional[EventType] = None) -> None:
        """Clear subscribers.

        Args:
            event_type: Specific event type to clear, or None to clear all.
        """
        if event_type is None:
            self._subscribers.clear()
        elif event_type in self._subscribers:
            self._subscribers.pop(event_type)


# Global singleton
event_bus = EventBus()