from __future__ import annotations

from backend.app.core.events.subscribers import EventSubscribers
from backend.app.core.events.types import DomainEvent


class EventPublisher:
    def __init__(self, subscribers: EventSubscribers) -> None:
        self._subscribers = subscribers

    def publish(self, event: DomainEvent) -> None:
        self._subscribers.notify(event)
