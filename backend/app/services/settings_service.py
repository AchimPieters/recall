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


class SettingsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SettingsRepository(db)
        self.security_repo = SecurityRepository(db)

    def get_all(self, organization_id: int | None = None) -> dict:
        return {s.key: s.value for s in self.repo.list_all(organization_id=organization_id)}

    def set_many(
        self,
        payload: dict,
        *,
        organization_id: int | None = None,
        changed_by: str = "system",
        reason: str = "update",
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "settings:write")

        unknown = sorted(set(payload) - ALLOWED_SETTING_KEYS)
        if unknown:
            raise ValueError(f"Unsupported setting keys: {', '.join(unknown)}")

        for key, value in payload.items():
            item = self.repo.upsert(key, str(value), organization_id=organization_id)
            self.repo.add_version(
                setting_key=item.key,
                setting_value=item.value,
                version=item.version,
                changed_by=changed_by,
                change_reason=reason,
                organization_id=organization_id,
            )

        self.security_repo.add_security_event(
            actor=changed_by,
            event_type="settings_change",
            detail=f"reason={reason},keys={','.join(sorted(payload.keys()))}",
            ip_address=None,
        )
        for key in sorted(payload.keys()):
            self.security_repo.add_audit_log(
                actor_type="user",
                actor_id=changed_by,
                organization_id=organization_id,
                action="settings.change",
                resource_type="setting",
                resource_id=key,
                before_state=None,
                after_state=str(payload[key]),
            )
        self.db.commit()
        return self.get_all(organization_id=organization_id)

    def get_history(
        self, key: str, *, organization_id: int | None = None, limit: int = 20
    ) -> list[dict]:
        return [
            {
                "setting_key": row.setting_key,
                "setting_value": row.setting_value,
                "version": row.version,
                "changed_by": row.changed_by,
                "change_reason": row.change_reason,
                "created_at": row.created_at,
            }
            for row in self.repo.list_versions(
                key, organization_id=organization_id, limit=max(1, min(limit, 200))
            )
        ]

    def rollback(
        self,
        *,
        key: str,
        target_version: int,
        organization_id: int | None = None,
        changed_by: str = "system",
        actor_role: str | None = None,
    ) -> dict:
        if actor_role is not None:
            enforce_role_permission(actor_role, "settings:write")

        snapshot = self.repo.get_version(
            key, target_version, organization_id=organization_id
        )
        if not snapshot:
            raise ValueError("Requested settings version does not exist")

        item = self.repo.upsert(
            key, snapshot.setting_value, organization_id=organization_id
        )
        self.repo.add_version(
            setting_key=item.key,
            setting_value=item.value,
            version=item.version,
            changed_by=changed_by,
            change_reason=f"rollback_to_v{target_version}",
            organization_id=organization_id,
        )
        self.security_repo.add_security_event(
            actor=changed_by,
            event_type="settings_rollback",
            detail=f"key={key},target_version={target_version},new_version={item.version}",
            ip_address=None,
        )
        self.security_repo.add_audit_log(
            actor_type="user",
            actor_id=changed_by,
            organization_id=organization_id,
            action="settings.rollback",
            resource_type="setting",
            resource_id=key,
            before_state=None,
            after_state=snapshot.setting_value,
        )
        self.db.commit()
        return {"key": item.key, "value": item.value, "version": item.version}
