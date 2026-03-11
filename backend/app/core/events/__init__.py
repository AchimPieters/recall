from backend.app.core.events.handlers import log_event
from backend.app.core.events.publisher import EventPublisher
from backend.app.core.events.subscribers import EventSubscribers
from backend.app.workers.event_handlers import (
    handle_alert_triggered,
    handle_device_registered,
    handle_media_uploaded,
    handle_ota_update_started,
    handle_playlist_updated,
)
from backend.app.core.events.types import (
    ALERT_TRIGGERED,
    DEVICE_REGISTERED,
    MEDIA_UPLOADED,
    OTA_UPDATE_STARTED,
    PLAYLIST_UPDATED,
    make_event,
)

subscribers = EventSubscribers()
subscribers.register(DEVICE_REGISTERED, log_event)
subscribers.register(DEVICE_REGISTERED, handle_device_registered)
subscribers.register(PLAYLIST_UPDATED, log_event)
subscribers.register(PLAYLIST_UPDATED, handle_playlist_updated)
subscribers.register(MEDIA_UPLOADED, log_event)
subscribers.register(MEDIA_UPLOADED, handle_media_uploaded)
subscribers.register(ALERT_TRIGGERED, log_event)
subscribers.register(ALERT_TRIGGERED, handle_alert_triggered)
subscribers.register(OTA_UPDATE_STARTED, log_event)
subscribers.register(OTA_UPDATE_STARTED, handle_ota_update_started)

publisher = EventPublisher(subscribers)

__all__ = [
    "publisher",
    "make_event",
    "DEVICE_REGISTERED",
    "PLAYLIST_UPDATED",
    "MEDIA_UPLOADED",
    "ALERT_TRIGGERED",
    "OTA_UPDATE_STARTED",
]
