from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_permission
from backend.app.db.database import get_db
from backend.app.models import Device, DeviceLog, Event

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", dependencies=[Depends(require_permission("monitor.read"))])
def analytics_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    org_id = user.organization_id

    total_devices_stmt = select(func.count(Device.id))
    online_devices_stmt = select(func.count(Device.id)).where(Device.status == "online")
    if org_id is not None:
        total_devices_stmt = total_devices_stmt.where(Device.organization_id == org_id)
        online_devices_stmt = online_devices_stmt.where(Device.organization_id == org_id)

    total_devices = int(db.scalar(total_devices_stmt) or 0)
    online_devices = int(db.scalar(online_devices_stmt) or 0)
    uptime_percent = round((online_devices / total_devices) * 100, 2) if total_devices else 0.0

    impressions_stmt = select(func.count(Event.id)).where(
        Event.category == "playback",
        Event.action == "impression",
    )
    if org_id is not None:
        impressions_stmt = impressions_stmt.where(Event.organization_id == org_id)
    impressions = int(db.scalar(impressions_stmt) or 0)

    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    log_scope = select(DeviceLog.id).join(Device, Device.id == DeviceLog.device_id).where(
        DeviceLog.timestamp >= window_start,
    )
    if org_id is not None:
        log_scope = log_scope.where(Device.organization_id == org_id)

    playback_errors_stmt = log_scope.where(func.lower(DeviceLog.level) == "error").with_only_columns(
        func.count(DeviceLog.id)
    )
    screen_activity_stmt = log_scope.with_only_columns(func.count(DeviceLog.id))

    playback_errors = int(db.scalar(playback_errors_stmt) or 0)
    screen_activity = int(db.scalar(screen_activity_stmt) or 0)

    return {
        "device_uptime_percent": uptime_percent,
        "content_impressions": impressions,
        "playback_errors_24h": playback_errors,
        "screen_activity_24h": screen_activity,
        "total_devices": total_devices,
    }
