from __future__ import annotations

from collections import defaultdict
from typing import Callable

from backend.app.core.events.types import DomainEvent

Subscriber = Callable[[DomainEvent], None]


class EventSubscribers:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Subscriber]] = defaultdict(list)

    def register(self, event_name: str, handler: Subscriber) -> None:
        self._handlers[event_name].append(handler)

    def notify(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.name, []):
            handler(event)
