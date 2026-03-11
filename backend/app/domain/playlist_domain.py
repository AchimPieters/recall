from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
import json


def normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_content_item(
    *,
    content_type: str,
    media_id: int | None,
    source_url: str | None,
    widget_config: str | None,
) -> None:
    allowed_content_types = {"image", "video", "web_url", "widget"}
    if content_type not in allowed_content_types:
        raise ValueError("unsupported content_type")
    if content_type in {"image", "video"} and media_id is None:
        raise ValueError("media_id is required for image/video items")
    if content_type == "web_url":
        if not source_url:
            raise ValueError("source_url is required for web_url items")
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute http(s) URL")
    if content_type == "widget":
        if not widget_config:
            raise ValueError("widget_config is required for widget items")
        try:
            parsed_widget = json.loads(widget_config)
        except json.JSONDecodeError as exc:
            raise ValueError("widget_config must be valid JSON") from exc
        if not isinstance(parsed_widget, dict):
            raise ValueError("widget_config must be a JSON object")


def validate_schedule_window(
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    starts_at = normalize_datetime(starts_at)
    ends_at = normalize_datetime(ends_at)
    if starts_at and ends_at and ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")
    return starts_at, ends_at
