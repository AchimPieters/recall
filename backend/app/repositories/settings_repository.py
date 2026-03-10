from sqlalchemy.orm import Session

from backend.app.models.settings import Setting, SettingVersion


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(
        self,
        *,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> list[Setting]:
        query = self.db.query(Setting).filter(Setting.scope == scope)
        if scope == "global":
            query = query.filter(Setting.organization_id.is_(None), Setting.device_id.is_(None))
        elif scope == "organization":
            query = query.filter(Setting.organization_id == organization_id, Setting.device_id.is_(None))
        else:
            query = query.filter(Setting.organization_id == organization_id, Setting.device_id == device_id)
        return query.all()

    def get_by_key(
        self,
        key: str,
        *,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> Setting | None:
        query = self.db.query(Setting).filter(Setting.key == key, Setting.scope == scope)
        if scope == "global":
            query = query.filter(Setting.organization_id.is_(None), Setting.device_id.is_(None))
        elif scope == "organization":
            query = query.filter(Setting.organization_id == organization_id, Setting.device_id.is_(None))
        else:
            query = query.filter(Setting.organization_id == organization_id, Setting.device_id == device_id)
        return query.first()

    def upsert(
        self,
        key: str,
        value: str,
        *,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> Setting:
        item = self.get_by_key(
            key,
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
        )
        if not item:
            item = Setting(
                key=key,
                scope=scope,
                organization_id=organization_id,
                device_id=device_id,
                version=1,
            )
            self.db.add(item)
        else:
            item.version = (item.version or 1) + 1
        item.value = value
        return item

    def add_version(
        self,
        *,
        setting_key: str,
        setting_value: str,
        version: int,
        changed_by: str,
        change_reason: str,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> SettingVersion:
        record = SettingVersion(
            setting_key=setting_key,
            setting_value=setting_value,
            version=version,
            scope=scope,
            organization_id=organization_id,
            device_id=device_id,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.db.add(record)
        return record

    def list_versions(
        self,
        setting_key: str,
        *,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
        limit: int = 50,
    ) -> list[SettingVersion]:
        query = self.db.query(SettingVersion).filter(
            SettingVersion.setting_key == setting_key,
            SettingVersion.scope == scope,
        )
        if scope == "global":
            query = query.filter(
                SettingVersion.organization_id.is_(None),
                SettingVersion.device_id.is_(None),
            )
        elif scope == "organization":
            query = query.filter(
                SettingVersion.organization_id == organization_id,
                SettingVersion.device_id.is_(None),
            )
        else:
            query = query.filter(
                SettingVersion.organization_id == organization_id,
                SettingVersion.device_id == device_id,
            )
        return query.order_by(SettingVersion.version.desc()).limit(limit).all()

    def get_version(
        self,
        setting_key: str,
        version: int,
        *,
        scope: str = "global",
        organization_id: int | None = None,
        device_id: str | None = None,
    ) -> SettingVersion | None:
        query = self.db.query(SettingVersion).filter(
            SettingVersion.setting_key == setting_key,
            SettingVersion.version == version,
            SettingVersion.scope == scope,
        )
        if scope == "global":
            query = query.filter(
                SettingVersion.organization_id.is_(None),
                SettingVersion.device_id.is_(None),
            )
        elif scope == "organization":
            query = query.filter(
                SettingVersion.organization_id == organization_id,
                SettingVersion.device_id.is_(None),
            )
        else:
            query = query.filter(
                SettingVersion.organization_id == organization_id,
                SettingVersion.device_id == device_id,
            )
        return query.first()
