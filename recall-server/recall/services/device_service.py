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
from recall.services.event_service import EventService

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
        self,
        device_id: str,
        name: str,
        ip: str | None,
        version: str | None,
        organization_id: int | None,
    ) -> Device:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            device = Device(id=device_id, name=name)
            self.db.add(device)
        device.status = "online"
        if device.organization_id is None:
            device.organization_id = organization_id
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

    def get_device(self, device_id: str) -> Device | None:
        return self.db.query(Device).filter(Device.id == device_id).first()

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

    def list_logs(
        self, limit: int = 100, organization_id: int | None = None
    ) -> list[DeviceLog]:
        query = self.db.query(DeviceLog).join(Device, Device.id == DeviceLog.device_id)
        if organization_id is not None:
            query = query.filter(Device.organization_id == organization_id)
        return (
            query.order_by(DeviceLog.timestamp.desc(), DeviceLog.id.desc())
            .limit(max(1, min(limit, 1000)))
            .all()
        )

    def mark_presence(self, organization_id: int | None = None) -> int:
        query = self.db.query(Device)
        if organization_id is not None:
            query = query.filter(Device.organization_id == organization_id)
        devices = query.all()
        now = self._utc_now()
        changed = 0
        for device in devices:
            if not device.last_seen:
                new_status = "stale"
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
                        organization_id=device.organization_id,
                    )
        self.db.commit()
        return changed

    def list_devices(self, organization_id: int | None = None) -> list[Device]:
        query = self.db.query(Device)
        if organization_id is not None:
            query = query.filter(Device.organization_id == organization_id)
        return query.all()

    def create_group(self, name: str, organization_id: int | None) -> DeviceGroup:
        existing = (
            self.db.query(DeviceGroup)
            .filter(
                DeviceGroup.name == name,
                DeviceGroup.organization_id == organization_id,
            )
            .first()
        )
        if existing:
            return existing
        group = DeviceGroup(name=name, organization_id=organization_id)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def list_groups(self, organization_id: int | None = None) -> list[DeviceGroup]:
        query = self.db.query(DeviceGroup)
        if organization_id is not None:
            query = query.filter(DeviceGroup.organization_id == organization_id)
        return query.order_by(DeviceGroup.name.asc()).all()

    def get_group(self, group_id: int) -> DeviceGroup | None:
        return self.db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()

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

    def list_group_members(self, group_id: int) -> list[DeviceGroupMember]:
        return (
            self.db.query(DeviceGroupMember)
            .filter(DeviceGroupMember.group_id == group_id)
            .all()
        )

    def execute_group_action(
        self,
        group_id: int,
        action: str,
        actor: str,
        organization_id: int | None,
        target_version: str | None = None,
        playlist_id: int | None = None,
    ) -> dict:
        valid_actions = {"reboot", "update", "playlist_assign", "rollback"}
        if action not in valid_actions:
            raise ValueError("unsupported action")

        group = self.get_group(group_id)
        if not group:
            raise ValueError("group not found")

        members = self.list_group_members(group_id)
        device_ids = [m.device_id for m in members]

        if action in {"update", "rollback"} and not target_version:
            raise ValueError("target_version is required for update/rollback")

        details: dict[str, str | int | None] = {"group_id": group_id, "action": action}
        if target_version:
            details["target_version"] = target_version
        if playlist_id is not None:
            details["playlist_id"] = playlist_id

        event = EventService(self.db).publish(
            category="device_group",
            action=f"bulk_{action}",
            actor=actor,
            payload={
                "group_id": group_id,
                "group_name": group.name,
                "device_ids": device_ids,
                "target_version": target_version,
                "playlist_id": playlist_id,
            },
            organization_id=organization_id,
        )

        for device_id in device_ids:
            message = f"bulk action={action}"
            if target_version:
                message += f" target_version={target_version}"
            if playlist_id is not None:
                message += f" playlist_id={playlist_id}"
            self.db.add(
                DeviceLog(
                    device_id=device_id,
                    level="info",
                    action=f"bulk_{action}",
                    message=message,
                )
            )
        self.db.commit()

        return {
            "group_id": group.id,
            "group_name": group.name,
            "action": action,
            "accepted": len(device_ids),
            "device_ids": device_ids,
            "event_id": event["id"],
            **details,
        }

    def record_screenshot(
        self, device_id: str, image_path: str, organization_id: int | None
    ) -> DeviceScreenshot:
        shot = DeviceScreenshot(
            device_id=device_id,
            image_path=image_path,
            organization_id=organization_id,
        )
        self.db.add(shot)
        self.db.commit()
        self.db.refresh(shot)
        return shot

    def list_screenshots(
        self, device_id: str | None = None, organization_id: int | None = None
    ) -> list[DeviceScreenshot]:
        query = self.db.query(DeviceScreenshot)
        if organization_id is not None:
            query = query.filter(DeviceScreenshot.organization_id == organization_id)
        if device_id:
            query = query.filter(DeviceScreenshot.device_id == device_id)
        return (
            query.order_by(
                DeviceScreenshot.captured_at.desc(), DeviceScreenshot.id.desc()
            )
            .limit(100)
            .all()
        )

    def create_alert(
        self, level: str, source: str, message: str, organization_id: int | None
    ) -> Alert:
        alert = Alert(
            level=level,
            source=source,
            message=message,
            status="open",
            organization_id=organization_id,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def list_alerts(
        self, status: str | None = None, organization_id: int | None = None
    ) -> list[Alert]:
        query = self.db.query(Alert)
        if organization_id is not None:
            query = query.filter(Alert.organization_id == organization_id)
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
