from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
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
    DeviceProvisioningToken,
    DeviceCertificate,
)
from backend.app.services.playlist_service import PlaylistService
from backend.app.services.event_service import EventService
from backend.app.core.events import (
    ALERT_TRIGGERED,
    DEVICE_REGISTERED,
    OTA_UPDATE_STARTED,
    make_event,
    publisher,
)
from backend.app.domain import select_rollout_devices

settings = get_settings()

ALERT_LEVELS = {"info", "warning", "critical"}
ALERT_STATUSES = {"open", "acknowledged", "resolved"}

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

    @staticmethod
    def _hash_value(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create_provisioning_token(
        self,
        *,
        actor: str,
        organization_id: int | None,
        expires_in_minutes: int = 30,
    ) -> dict:
        expires_in_minutes = max(1, min(expires_in_minutes, 24 * 60))
        raw_token = secrets.token_urlsafe(24)
        token_hash = self._hash_value(raw_token)
        expires_at = self._utc_now() + timedelta(minutes=expires_in_minutes)
        row = DeviceProvisioningToken(
            token_hash=token_hash,
            organization_id=organization_id,
            expires_at=expires_at,
            created_by=actor,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return {
            "token": raw_token,
            "expires_at": row.expires_at,
            "organization_id": row.organization_id,
            "id": row.id,
        }

    def enroll_device_with_token(
        self,
        *,
        provisioning_token: str,
        device_id: str,
        name: str,
        ip: str | None,
        version: str | None,
        capabilities: dict | None = None,
    ) -> dict:
        token_hash = self._hash_value(provisioning_token)
        token_row = (
            self.db.query(DeviceProvisioningToken)
            .filter(DeviceProvisioningToken.token_hash == token_hash)
            .first()
        )
        now = self._utc_now()
        expires_at = self._normalize(token_row.expires_at) if token_row else None
        if (
            not token_row
            or token_row.used_at is not None
            or expires_at is None
            or expires_at < now
        ):
            raise ValueError("invalid or expired provisioning token")

        device = self.register(
            device_id=device_id,
            name=name,
            ip=ip,
            version=version,
            organization_id=token_row.organization_id,
            capabilities=capabilities,
        )

        cert_seed = f"{device.id}:{now.isoformat()}:{secrets.token_hex(16)}"
        fingerprint = self._hash_value(cert_seed)
        certificate_pem = f"-----BEGIN DEVICE CERTIFICATE-----\n{fingerprint}\n-----END DEVICE CERTIFICATE-----"
        cert = DeviceCertificate(
            device_id=device.id,
            certificate_pem=certificate_pem,
            fingerprint=fingerprint,
            issued_at=now,
            expires_at=now + timedelta(days=365),
        )
        token_row.used_at = now
        self.db.add(cert)
        self.db.commit()

        return {
            "device_id": device.id,
            "organization_id": device.organization_id,
            "certificate": certificate_pem,
            "certificate_fingerprint": fingerprint,
            "provisioned_at": now.isoformat(),
        }

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
        publisher.publish(
            make_event(
                DEVICE_REGISTERED,
                {"device_id": device_id, "organization_id": organization_id},
            )
        )
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
        resolved = playlist_service.resolve_for_device(device_id)
        playlist_id = resolved.get("playlist_id")
        zone_plan = playlist_service.resolve_zone_playback_plan(device_id)
        payload = {
            "device_id": device_id,
            "heartbeat_interval": 30,
            "fallback_content": "default",
            "active_playlist_id": playlist_id,
            "zone_plan": zone_plan,
        }

        active_media = playlist_service.resolve_active_media_asset(device_id)
        if active_media:
            payload["active_media_id"] = active_media.get("media_id")
            payload["active_media_path"] = active_media.get("path")
            payload["active_media_checksum"] = active_media.get("checksum")

        return payload

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
            age = (
                now - (self._normalize(device.last_seen) or now)
                if device.last_seen
                else None
            )
            if not device.last_seen:
                new_status = "stale"
            elif age and age > timedelta(seconds=settings.heartbeat_timeout_seconds):
                new_status = "offline"
            elif age and age > timedelta(
                seconds=max(5, settings.heartbeat_timeout_seconds // 2)
            ):
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
            query = query.join(
                DeviceGroupMember, DeviceGroupMember.device_id == Device.id
            ).filter(DeviceGroupMember.group_id == group_id)
        if tag:
            query = (
                query.join(DeviceTagLink, DeviceTagLink.device_id == Device.id)
                .join(DeviceTag, DeviceTag.id == DeviceTagLink.tag_id)
                .filter(DeviceTag.name == tag)
            )
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
        rollout_percentage: int = 100,
        dry_run: bool = False,
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "devices.manage")

        valid_actions = {"reboot", "update", "playlist_assign", "rollback"}
        if action not in valid_actions:
            raise ValueError("unsupported action")
        if rollout_percentage < 1 or rollout_percentage > 100:
            raise ValueError("rollout_percentage must be between 1 and 100")

        group = self.get_group(group_id)
        if not group:
            raise ValueError("group not found")

        members = self.list_group_members(group_id)
        device_ids = [m.device_id for m in members]

        if action in {"update", "rollback"} and not target_version:
            raise ValueError("target_version is required for update/rollback")

        selected_device_ids = select_rollout_devices(device_ids, rollout_percentage)

        incompatible_device_ids: list[str] = []
        if action == "rollback" and target_version:
            known_versions = self._group_known_versions(device_ids)
            if target_version not in known_versions:
                raise ValueError(
                    "unknown rollback target_version for group: " f"{target_version}"
                )

        if action in {"update", "rollback"} and target_version:
            incompatible_device_ids = self._find_incompatible_devices(
                selected_device_ids,
                target_version,
                action,
            )
            if incompatible_device_ids:
                raise ValueError(
                    "incompatible target_version for devices: "
                    + ",".join(sorted(incompatible_device_ids))
                )

        details: dict[str, str | int | None] = {"group_id": group_id, "action": action}
        if target_version:
            details["target_version"] = target_version
        if playlist_id is not None:
            details["playlist_id"] = playlist_id
        details["rollout_percentage"] = rollout_percentage
        details["selected"] = len(selected_device_ids)
        details["deferred"] = len(device_ids) - len(selected_device_ids)
        details["dry_run"] = dry_run

        if dry_run:
            return {
                "group_id": group.id,
                "group_name": group.name,
                "action": action,
                "accepted": len(selected_device_ids),
                "device_ids": selected_device_ids,
                "deferred_device_ids": [
                    d for d in device_ids if d not in set(selected_device_ids)
                ],
                **details,
            }

        event = EventService(self.db).publish(
            category="device_group",
            action=f"bulk_{action}",
            actor=actor,
            payload={
                "group_id": group_id,
                "group_name": group.name,
                "device_ids": selected_device_ids,
                "target_version": target_version,
                "playlist_id": playlist_id,
                "rollout_percentage": rollout_percentage,
            },
            organization_id=organization_id,
        )

        if action == "update":
            publisher.publish(
                make_event(
                    OTA_UPDATE_STARTED,
                    {
                        "group_id": group_id,
                        "target_version": target_version,
                        "device_ids": selected_device_ids,
                    },
                )
            )

        for device_id in selected_device_ids:
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
            "accepted": len(selected_device_ids),
            "device_ids": selected_device_ids,
            "deferred_device_ids": [
                d for d in device_ids if d not in set(selected_device_ids)
            ],
            "event_id": event["id"],
            **details,
        }

    @staticmethod
    def _parse_semver(version: str | None) -> tuple[int, int, int] | None:
        if not version:
            return None
        match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", version.strip())
        if not match:
            return None
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    def _group_known_versions(self, device_ids: list[str]) -> set[str]:
        if not device_ids:
            return set()
        rows = (
            self.db.query(Device.version)
            .filter(Device.id.in_(device_ids), Device.version.isnot(None))
            .all()
        )
        return {str(row[0]) for row in rows if row and row[0]}

    def _find_incompatible_devices(
        self,
        device_ids: list[str],
        target_version: str,
        action: str,
    ) -> list[str]:
        target = self._parse_semver(target_version)
        if not target:
            return device_ids

        incompatible: list[str] = []
        for device_id in device_ids:
            device = self.get_device(device_id)
            current = self._parse_semver(device.version if device else None)
            if not current:
                incompatible.append(device_id)
                continue
            if current[0] != target[0]:
                incompatible.append(device_id)
                continue
            if action == "update" and current >= target:
                incompatible.append(device_id)
            if action == "rollback" and current <= target:
                incompatible.append(device_id)
        return incompatible

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
            .filter(
                DeviceTag.name == name, DeviceTag.organization_id == organization_id
            )
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

    def assign_tag(
        self, device_id: str, tag_name: str, organization_id: int | None
    ) -> dict:
        tag = self.create_tag(tag_name, organization_id)
        existing = (
            self.db.query(DeviceTagLink)
            .filter(
                DeviceTagLink.device_id == device_id, DeviceTagLink.tag_id == tag.id
            )
            .first()
        )
        if not existing:
            self.db.add(DeviceTagLink(device_id=device_id, tag_id=tag.id))
            self.db.commit()
        return {"device_id": device_id, "tag_id": tag.id, "tag_name": tag.name}

    def create_alert(
        self, level: str, source: str, message: str, organization_id: int | None
    ) -> Alert:
        normalized_level = (level or "").strip().lower()
        if normalized_level not in ALERT_LEVELS:
            raise ValueError(f"unsupported alert level: {level}")

        alert = Alert(
            level=normalized_level,
            source=source,
            message=message,
            status="open",
            organization_id=organization_id,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        publisher.publish(
            make_event(
                ALERT_TRIGGERED, {"alert_id": alert.id, "level": normalized_level}
            )
        )
        return alert

    def list_alerts(
        self, status: str | None = None, organization_id: int | None = None
    ) -> list[Alert]:
        query = self.db.query(Alert)
        if organization_id is not None:
            query = query.filter(Alert.organization_id == organization_id)
        if status:
            normalized_status = status.strip().lower()
            if normalized_status not in ALERT_STATUSES:
                raise ValueError(f"unsupported alert status: {status}")
            query = query.filter(Alert.status == normalized_status)
        return query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(200).all()

    def resolve_alert(self, alert_id: int) -> Alert | None:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        if alert.status == "resolved":
            return alert
        alert.status = "resolved"
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge_alert(self, alert_id: int) -> Alert | None:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        if alert.status in {"acknowledged", "resolved"}:
            return alert
        alert.status = "acknowledged"
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
        return [
            c
            for c in _device_command_queue.get(device_id, [])
            if c.get("status") == "pending"
        ]

    def ack_command(
        self, device_id: str, command_id: str, status: str, detail: str | None = None
    ) -> dict | None:
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
