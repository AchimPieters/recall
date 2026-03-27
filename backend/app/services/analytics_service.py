from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Device, DeviceLog, Event


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _day_bucket_utc(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).date().isoformat()

    def summary(self, organization_id: int | None) -> dict[str, float | int]:
        total_devices_stmt = select(func.count(Device.id))
        online_devices_stmt = select(func.count(Device.id)).where(
            Device.status == "online"
        )
        if organization_id is not None:
            total_devices_stmt = total_devices_stmt.where(
                Device.organization_id == organization_id
            )
            online_devices_stmt = online_devices_stmt.where(
                Device.organization_id == organization_id
            )

        total_devices = int(self.db.scalar(total_devices_stmt) or 0)
        online_devices = int(self.db.scalar(online_devices_stmt) or 0)
        uptime_percent = (
            round((online_devices / total_devices) * 100, 2) if total_devices else 0.0
        )

        impressions_stmt = select(func.count(Event.id)).where(
            Event.category == "playback",
            Event.action == "impression",
        )
        if organization_id is not None:
            impressions_stmt = impressions_stmt.where(
                Event.organization_id == organization_id
            )
        impressions = int(self.db.scalar(impressions_stmt) or 0)

        window_start = datetime.now(timezone.utc) - timedelta(hours=24)
        log_scope = (
            select(DeviceLog.id)
            .join(Device, Device.id == DeviceLog.device_id)
            .where(DeviceLog.timestamp >= window_start)
        )
        if organization_id is not None:
            log_scope = log_scope.where(Device.organization_id == organization_id)

        playback_errors_stmt = log_scope.where(
            func.lower(DeviceLog.level) == "error"
        ).with_only_columns(func.count(DeviceLog.id))
        screen_activity_stmt = log_scope.with_only_columns(func.count(DeviceLog.id))

        playback_errors = int(self.db.scalar(playback_errors_stmt) or 0)
        screen_activity = int(self.db.scalar(screen_activity_stmt) or 0)

        return {
            "device_uptime_percent": uptime_percent,
            "content_impressions": impressions,
            "playback_errors_24h": playback_errors,
            "screen_activity_24h": screen_activity,
            "total_devices": total_devices,
        }

    def timeseries(
        self, organization_id: int | None, days: int
    ) -> dict[str, int | list[dict[str, int | str]]]:
        today = datetime.now(timezone.utc).date()
        start_day = today - timedelta(days=days - 1)
        start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)

        impressions_stmt = select(Event.created_at).where(
            Event.category == "playback",
            Event.action == "impression",
            Event.created_at >= start_dt,
        )
        if organization_id is not None:
            impressions_stmt = impressions_stmt.where(
                Event.organization_id == organization_id
            )

        playback_stmt = (
            select(DeviceLog.timestamp)
            .join(Device, Device.id == DeviceLog.device_id)
            .where(
                DeviceLog.timestamp >= start_dt, func.lower(DeviceLog.level) == "error"
            )
        )
        if organization_id is not None:
            playback_stmt = playback_stmt.where(
                Device.organization_id == organization_id
            )

        impression_map: dict[str, int] = {}
        for created_at in self.db.scalars(impressions_stmt):
            if created_at is None:
                continue
            key = self._day_bucket_utc(created_at)
            impression_map[key] = impression_map.get(key, 0) + 1

        playback_map: dict[str, int] = {}
        for logged_at in self.db.scalars(playback_stmt):
            if logged_at is None:
                continue
            key = self._day_bucket_utc(logged_at)
            playback_map[key] = playback_map.get(key, 0) + 1

        points: list[dict[str, int | str]] = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            key = day.isoformat()
            points.append(
                {
                    "date": key,
                    "content_impressions": impression_map.get(key, 0),
                    "playback_errors": playback_map.get(key, 0),
                }
            )

        return {"window_days": days, "points": points}
