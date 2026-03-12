from sqlalchemy.orm import Session

from backend.app.core.auth import enforce_role_permission
from backend.app.repositories import SettingsRepository
from backend.app.repositories.security_repository import SecurityRepository

ALLOWED_SETTING_KEYS = {
    "site_name",
    "timezone",
    "language",
    "heartbeat_interval",
    "default_playlist_id",
    "display_brightness",
    "volume",
}

SCOPE_GLOBAL = "global"
SCOPE_ORGANIZATION = "organization"
SCOPE_DEVICE = "device"
ALLOWED_SCOPES = {SCOPE_GLOBAL, SCOPE_ORGANIZATION, SCOPE_DEVICE}


class SettingsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SettingsRepository(db)
        self.security_repo = SecurityRepository(db)

    def _validate_target(
        self,
        *,
        scope: str,
        organization_id: int | None,
        device_id: str | None,
    ) -> None:
        if scope not in ALLOWED_SCOPES:
            raise ValueError(f"Unsupported settings scope: {scope}")
        if scope == SCOPE_GLOBAL and (
            organization_id is not None or device_id is not None
        ):
            raise ValueError("Global settings cannot target organization or device")
        if scope == SCOPE_ORGANIZATION:
            if organization_id is None:
                raise ValueError("Organization settings require organization_id")
            if device_id is not None:
                raise ValueError("Organization settings cannot target device_id")
        if scope == SCOPE_DEVICE and (organization_id is None or not device_id):
            raise ValueError("Device settings require organization_id and device_id")

    def _validate_values(self, payload: dict) -> None:
        unknown = sorted(set(payload) - ALLOWED_SETTING_KEYS)
        if unknown:
            raise ValueError(f"Unsupported setting keys: {', '.join(unknown)}")

        if "heartbeat_interval" in payload:
            value = int(payload["heartbeat_interval"])
            if value < 5 or value > 3600:
                raise ValueError(
                    "heartbeat_interval must be between 5 and 3600 seconds"
                )

        if "display_brightness" in payload:
            value = int(payload["display_brightness"])
            if value < 0 or value > 100:
                raise ValueError("display_brightness must be between 0 and 100")

        if "volume" in payload:
            value = int(payload["volume"])
            if value < 0 or value > 100:
                raise ValueError("volume must be between 0 and 100")

    def get_all(
        self,
        *,
        scope: str,
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> dict:
        self._validate_target(
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        return {
            s.key: s.value
            for s in self.repo.list_all(
                scope=scope,
                organization_id=organization_id,
                device_id=device_id,
            )
        }

    def set_many(
        self,
        payload: dict,
        *,
        scope: str,
        organization_id: int | None = None,
        device_id: str | None = None,
        changed_by: str = "system",
        reason: str = "update",
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "settings:write")

        self._validate_target(
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        self._validate_values(payload)

        for key, value in payload.items():
            item = self.repo.upsert(
                key,
                str(value),
                scope=scope,
                organization_id=organization_id,
                device_id=device_id,
            )
            self.repo.add_version(
                setting_key=item.key,
                setting_value=item.value,
                version=item.version,
                changed_by=changed_by,
                change_reason=reason,
                scope=scope,
                organization_id=organization_id,
                device_id=device_id,
            )

        self.security_repo.add_security_event(
            actor=changed_by,
            event_type="settings_change",
            detail=f"scope={scope},reason={reason},keys={','.join(sorted(payload.keys()))}",
            ip_address=None,
        )
        for key in sorted(payload.keys()):
            self.security_repo.add_audit_log(
                actor_type="user",
                actor_id=changed_by,
                organization_id=organization_id,
                action="settings.change",
                resource_type="setting",
                resource_id=f"{scope}:{device_id or '-'}:{key}",
                before_state=None,
                after_state=str(payload[key]),
            )
        self.db.commit()
        return self.get_all(
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )

    def get_history(
        self,
        key: str,
        *,
        scope: str,
        organization_id: int | None = None,
        device_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        self._validate_target(
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        return [
            {
                "setting_key": row.setting_key,
                "setting_value": row.setting_value,
                "version": row.version,
                "scope": row.scope,
                "organization_id": row.organization_id,
                "device_id": row.device_id,
                "changed_by": row.changed_by,
                "change_reason": row.change_reason,
                "created_at": row.created_at,
            }
            for row in self.repo.list_versions(
                key,
                scope=scope,
                organization_id=organization_id,
                device_id=device_id,
                limit=max(1, min(limit, 200)),
            )
        ]

    def rollback(
        self,
        *,
        key: str,
        target_version: int,
        scope: str,
        organization_id: int | None = None,
        device_id: str | None = None,
        changed_by: str = "system",
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "settings:write")

        self._validate_target(
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )

        snapshot = self.repo.get_version(
            key,
            target_version,
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        if not snapshot:
            raise ValueError("Requested settings version does not exist")

        item = self.repo.upsert(
            key,
            snapshot.setting_value,
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        self.repo.add_version(
            setting_key=item.key,
            setting_value=item.value,
            version=item.version,
            changed_by=changed_by,
            change_reason=f"rollback_to_v{target_version}",
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        self.security_repo.add_security_event(
            actor=changed_by,
            event_type="settings_rollback",
            detail=(
                f"scope={scope},device_id={device_id},key={key},"
                f"target_version={target_version},new_version={item.version}"
            ),
            ip_address=None,
        )
        self.security_repo.add_audit_log(
            actor_type="user",
            actor_id=changed_by,
            organization_id=organization_id,
            action="settings.rollback",
            resource_type="setting",
            resource_id=f"{scope}:{device_id or '-'}:{key}",
            before_state=None,
            after_state=snapshot.setting_value,
        )
        self.db.commit()
        return {
            "key": item.key,
            "value": item.value,
            "version": item.version,
            "scope": scope,
            "organization_id": organization_id,
            "device_id": device_id,
        }
