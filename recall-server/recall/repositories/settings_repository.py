from sqlalchemy.orm import Session

from recall.models.settings import Setting


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Setting]:
        return self.db.query(Setting).all()

    def get_by_key(self, key: str) -> Setting | None:
        return self.db.query(Setting).filter(Setting.key == key).first()

    def upsert(self, key: str, value: str) -> Setting:
        item = self.get_by_key(key)
        if not item:
            item = Setting(key=key)
            self.db.add(item)
        item.value = value
        return item
