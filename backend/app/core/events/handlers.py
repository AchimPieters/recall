from __future__ import annotations

import logging

from backend.app.core.events.types import DomainEvent

logger = logging.getLogger("recall.events")


def log_event(event: DomainEvent) -> None:
    logger.info("domain_event name=%s payload=%s", event.name, event.payload)
