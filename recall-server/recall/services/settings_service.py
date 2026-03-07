from sqlalchemy.orm import Session

from recall.repositories import SettingsRepository

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

    def get_all(self) -> dict:
        return {s.key: s.value for s in self.repo.list_all()}

    def set_many(self, payload: dict) -> dict:
        unknown = sorted(set(payload) - ALLOWED_SETTING_KEYS)
        if unknown:
            raise ValueError(f"Unsupported setting keys: {', '.join(unknown)}")
        for key, value in payload.items():
            self.repo.upsert(key, str(value))
        self.db.commit()
        return self.get_all()
