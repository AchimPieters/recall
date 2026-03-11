from __future__ import annotations

from backend.app.core.events.types import DomainEvent


def handle_device_registered(event: DomainEvent) -> None:
    _ = event


def handle_playlist_updated(event: DomainEvent) -> None:
    _ = event


def handle_media_uploaded(event: DomainEvent) -> None:
    _ = event


def handle_alert_triggered(event: DomainEvent) -> None:
    _ = event


def handle_ota_update_started(event: DomainEvent) -> None:
    _ = event
