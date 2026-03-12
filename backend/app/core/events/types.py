from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    occurred_at: datetime


def make_event(name: str, payload: dict[str, Any]) -> DomainEvent:
    return DomainEvent(
        name=name, payload=payload, occurred_at=datetime.now(timezone.utc)
    )


DEVICE_REGISTERED = "device_registered"
PLAYLIST_UPDATED = "playlist_updated"
MEDIA_UPLOADED = "media_uploaded"
ALERT_TRIGGERED = "alert_triggered"
OTA_UPDATE_STARTED = "ota_update_started"
