from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from recall.core.config import get_settings
from recall.models.device import (
    Alert,
    Device,
    DeviceGroup,
    DeviceGroupMember,
    DeviceLog,
    DeviceScreenshot,
)
from recall.services.playlist_service import PlaylistService

settings = get_settings()


class DeviceService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def register(
        self, device_id: str, name: str, ip: str | None, version: str | None
    ) -> Device:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            device = Device(id=device_id, name=name)
            self.db.add(device)
        device.status = "online"
        device.ip = ip
        device.version = version
        device.last_seen = self._utc_now()
        self.db.commit()
        self.db.refresh(device)
        return device

    def heartbeat(self, device_id: str, metrics: dict | None = None) -> Device | None:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return None
        device.last_seen = self._utc_now()
        device.status = "online"
        device.metrics = metrics
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_config(self, device_id: str) -> dict:
        playlist_id = PlaylistService(self.db).resolve_active_playlist_id(device_id)
        return {
            "device_id": device_id,
            "heartbeat_interval": 30,
            "fallback_content": "default",
            "active_playlist_id": playlist_id,
        }

    def add_log(
        self, device_id: str, level: str, action: str, message: str
    ) -> DeviceLog:
        log = DeviceLog(
            device_id=device_id, level=level, action=action, message=message
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(self, limit: int = 100) -> list[DeviceLog]:
        return (
            self.db.query(DeviceLog)
            .order_by(DeviceLog.timestamp.desc(), DeviceLog.id.desc())
            .limit(max(1, min(limit, 1000)))
            .all()
        )

    def mark_presence(self) -> int:
        devices = self.db.query(Device).all()
        now = self._utc_now()
        changed = 0
        for device in devices:
            if not device.last_seen:
                new_status = "unreachable"
            elif now - (self._normalize(device.last_seen) or now) > timedelta(
                seconds=settings.heartbeat_timeout_seconds
            ):
                new_status = "offline"
            else:
                new_status = "online"
            if device.status != new_status:
                changed += 1
                device.status = new_status
                if new_status == "offline":
                    self.create_alert(
                        level="warning",
                        source="device",
                        message=f"Device {device.id} went offline",
                    )
        self.db.commit()
        return changed

    def list_devices(self) -> list[Device]:
        return self.db.query(Device).all()

    def create_group(self, name: str) -> DeviceGroup:
        existing = self.db.query(DeviceGroup).filter(DeviceGroup.name == name).first()
        if existing:
            return existing
        group = DeviceGroup(name=name)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def list_groups(self) -> list[DeviceGroup]:
        return self.db.query(DeviceGroup).order_by(DeviceGroup.name.asc()).all()

    def assign_group_member(self, group_id: int, device_id: str) -> DeviceGroupMember:
        existing = (
            self.db.query(DeviceGroupMember)
            .filter(
                DeviceGroupMember.group_id == group_id,
                DeviceGroupMember.device_id == device_id,
            )
            .first()
        )
        if existing:
            return existing
        member = DeviceGroupMember(group_id=group_id, device_id=device_id)
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def record_screenshot(self, device_id: str, image_path: str) -> DeviceScreenshot:
        shot = DeviceScreenshot(device_id=device_id, image_path=image_path)
        self.db.add(shot)
        self.db.commit()
        self.db.refresh(shot)
        return shot

    def list_screenshots(self, device_id: str | None = None) -> list[DeviceScreenshot]:
        query = self.db.query(DeviceScreenshot)
        if device_id:
            query = query.filter(DeviceScreenshot.device_id == device_id)
        return (
            query.order_by(
                DeviceScreenshot.captured_at.desc(), DeviceScreenshot.id.desc()
            )
            .limit(100)
            .all()
        )

    def create_alert(self, level: str, source: str, message: str) -> Alert:
        alert = Alert(level=level, source=source, message=message, status="open")
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def list_alerts(self, status: str | None = None) -> list[Alert]:
        query = self.db.query(Alert)
        if status:
            query = query.filter(Alert.status == status)
        return query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(200).all()

    def resolve_alert(self, alert_id: int) -> Alert | None:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        alert.status = "resolved"
        self.db.commit()
        self.db.refresh(alert)
        return alert
