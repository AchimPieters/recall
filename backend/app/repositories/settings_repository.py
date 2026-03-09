from sqlalchemy.orm import Session

from backend.app.models.settings import Setting, SettingVersion


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, organization_id: int | None = None) -> list[Setting]:
        query = self.db.query(Setting)
        if organization_id is not None:
            query = query.filter(Setting.organization_id == organization_id)
        else:
            query = query.filter(Setting.organization_id.is_(None))
        return query.all()

    def get_by_key(self, key: str, organization_id: int | None = None) -> Setting | None:
        query = self.db.query(Setting).filter(Setting.key == key)
        if organization_id is not None:
            query = query.filter(Setting.organization_id == organization_id)
        else:
            query = query.filter(Setting.organization_id.is_(None))
        return query.first()

    def upsert(self, key: str, value: str, organization_id: int | None = None) -> Setting:
        item = self.get_by_key(key, organization_id=organization_id)
        if not item:
            item = Setting(key=key, organization_id=organization_id, version=1)
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
        organization_id: int | None = None,
    ) -> SettingVersion:
        record = SettingVersion(
            setting_key=setting_key,
            setting_value=setting_value,
            version=version,
            changed_by=changed_by,
            change_reason=change_reason,
            organization_id=organization_id,
        )
        self.db.add(record)
        return record

    def list_versions(
        self,
        setting_key: str,
        organization_id: int | None = None,
        limit: int = 50,
    ) -> list[SettingVersion]:
        query = self.db.query(SettingVersion).filter(SettingVersion.setting_key == setting_key)
        if organization_id is not None:
            query = query.filter(SettingVersion.organization_id == organization_id)
        else:
            query = query.filter(SettingVersion.organization_id.is_(None))
        return query.order_by(SettingVersion.version.desc()).limit(limit).all()

    def get_version(
        self,
        setting_key: str,
        version: int,
        organization_id: int | None = None,
    ) -> SettingVersion | None:
        query = self.db.query(SettingVersion).filter(
            SettingVersion.setting_key == setting_key,
            SettingVersion.version == version,
        )
        if organization_id is not None:
            query = query.filter(SettingVersion.organization_id == organization_id)
        else:
            query = query.filter(SettingVersion.organization_id.is_(None))
        return query.first()
