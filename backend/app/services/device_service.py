from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from backend.app.core.auth import enforce_role_permission
from backend.app.core.config import get_settings
from backend.app.models.device import (
    Alert,
    Device,
    DeviceGroup,
    DeviceGroupMember,
    DeviceLog,
    DeviceScreenshot,
    DeviceTag,
    DeviceTagLink,
)
from backend.app.services.playlist_service import PlaylistService
from backend.app.services.event_service import EventService

settings = get_settings()


_device_command_queue: dict[str, list[dict]] = {}


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
        capabilities: dict | None = None,
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
        if capabilities is not None:
            device.capabilities = capabilities
        device.last_seen = self._utc_now()
        self.db.commit()
        self.db.refresh(device)
        return device

    def heartbeat(self, device_id: str, metrics: dict | None = None) -> Device | None:
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return None
        device.last_seen = self._utc_now()
        metric_state = str((metrics or {}).get("state", "")).lower() if metrics else ""
        if metric_state == "error":
            device.status = "error"
        else:
            device.status = "online"
        device.metrics = metrics
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_device(self, device_id: str) -> Device | None:
        return self.db.query(Device).filter(Device.id == device_id).first()

    def get_config(self, device_id: str) -> dict:
        playlist_service = PlaylistService(self.db)
        playlist_id = playlist_service.resolve_active_playlist_id(device_id)
        zone_plan = playlist_service.resolve_zone_playback_plan(device_id)
        return {
            "device_id": device_id,
            "heartbeat_interval": 30,
            "fallback_content": "default",
            "active_playlist_id": playlist_id,
            "zone_plan": zone_plan,
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
            age = now - (self._normalize(device.last_seen) or now) if device.last_seen else None
            if not device.last_seen:
                new_status = "stale"
            elif age and age > timedelta(seconds=settings.heartbeat_timeout_seconds):
                new_status = "offline"
            elif age and age > timedelta(seconds=max(5, settings.heartbeat_timeout_seconds // 2)):
                new_status = "stale"
            elif device.status == "error":
                new_status = "error"
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

    def list_devices(
        self,
        organization_id: int | None = None,
        status: str | None = None,
        group_id: int | None = None,
        tag: str | None = None,
        version: str | None = None,
        last_seen_before: datetime | None = None,
    ) -> list[Device]:
        query = self.db.query(Device)
        if organization_id is not None:
            query = query.filter(Device.organization_id == organization_id)
        if status:
            query = query.filter(Device.status == status)
        if version:
            query = query.filter(Device.version == version)
        if last_seen_before is not None:
            query = query.filter(Device.last_seen <= last_seen_before)
        if group_id is not None:
            query = query.join(DeviceGroupMember, DeviceGroupMember.device_id == Device.id).filter(
                DeviceGroupMember.group_id == group_id
            )
        if tag:
            query = query.join(DeviceTagLink, DeviceTagLink.device_id == Device.id).join(
                DeviceTag, DeviceTag.id == DeviceTagLink.tag_id
            ).filter(DeviceTag.name == tag)
        return query.order_by(Device.id.asc()).all()

    def create_group(
        self,
        name: str,
        organization_id: int | None,
        actor_role: str | None = None,
    ) -> DeviceGroup:
        if actor_role is not None:
            enforce_role_permission(actor_role, "devices.write")

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

    def assign_group_member(
        self,
        group_id: int,
        device_id: str,
        actor_role: str | None = None,
    ) -> DeviceGroupMember:
        if actor_role is not None:
            enforce_role_permission(actor_role, "devices.write")

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
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "devices.manage")

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

    def create_tag(self, name: str, organization_id: int | None) -> DeviceTag:
        existing = (
            self.db.query(DeviceTag)
            .filter(DeviceTag.name == name, DeviceTag.organization_id == organization_id)
            .first()
        )
        if existing:
            return existing
        tag = DeviceTag(name=name, organization_id=organization_id)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def list_tags(self, organization_id: int | None = None) -> list[DeviceTag]:
        query = self.db.query(DeviceTag)
        if organization_id is not None:
            query = query.filter(DeviceTag.organization_id == organization_id)
        return query.order_by(DeviceTag.name.asc()).all()

    def assign_tag(self, device_id: str, tag_name: str, organization_id: int | None) -> dict:
        tag = self.create_tag(tag_name, organization_id)
        existing = (
            self.db.query(DeviceTagLink)
            .filter(DeviceTagLink.device_id == device_id, DeviceTagLink.tag_id == tag.id)
            .first()
        )
        if not existing:
            self.db.add(DeviceTagLink(device_id=device_id, tag_id=tag.id))
            self.db.commit()
        return {"device_id": device_id, "tag_id": tag.id, "tag_name": tag.name}

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


    def enqueue_command(
        self,
        *,
        device_id: str,
        command_type: str,
        payload: dict | None = None,
        organization_id: int | None = None,
    ) -> dict:
        command = {
            "command_id": uuid4().hex,
            "type": command_type,
            "payload": payload or {},
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        _device_command_queue.setdefault(device_id, []).append(command)
        EventService(self.db).publish(
            category="device_command",
            action="enqueue",
            actor="system",
            payload={"device_id": device_id, "command": command},
            organization_id=organization_id,
        )
        return command

    def fetch_commands(self, device_id: str) -> list[dict]:
        return [c for c in _device_command_queue.get(device_id, []) if c.get("status") == "pending"]

    def ack_command(self, device_id: str, command_id: str, status: str, detail: str | None = None) -> dict | None:
        for command in _device_command_queue.get(device_id, []):
            if command["command_id"] == command_id:
                command["status"] = status
                command["acked_at"] = datetime.now(timezone.utc).isoformat()
                command["detail"] = detail
                return command
        return None

    def record_playback_status(
        self,
        *,
        device_id: str,
        state: str,
        media_id: int | None = None,
        position_seconds: int | None = None,
        detail: str | None = None,
    ) -> None:
        message = f"state={state}"
        if media_id is not None:
            message += f" media_id={media_id}"
        if position_seconds is not None:
            message += f" position_seconds={position_seconds}"
        if detail:
            message += f" detail={detail}"
        self.db.add(
            DeviceLog(
                device_id=device_id,
                level="info",
                action="playback_status",
                message=message,
            )
        )
        self.db.commit()
