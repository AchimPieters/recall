from sqlalchemy.orm import Session
from recall.models.settings import Setting


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

    def get_all(self) -> dict:
        return {s.key: s.value for s in self.db.query(Setting).all()}

    def set_many(self, payload: dict) -> dict:
        unknown = sorted(set(payload) - ALLOWED_SETTING_KEYS)
        if unknown:
            raise ValueError(f"Unsupported setting keys: {', '.join(unknown)}")
        for key, value in payload.items():
            item = self.db.query(Setting).filter(Setting.key == key).first()
            if not item:
                item = Setting(key=key)
                self.db.add(item)
            item.value = str(value)
        self.db.commit()
        return self.get_all()
