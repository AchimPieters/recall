from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.core.config import get_settings

settings = get_settings()


class SecretRotationService:
    @staticmethod
    def _parse_iso8601(value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def is_rotation_due(
        self,
        *,
        now: datetime | None = None,
        last_rotated_at: str | None,
    ) -> bool:
        if settings.secret_rotation_max_age_days <= 0:
            return False
        parsed = self._parse_iso8601(last_rotated_at)
        if parsed is None:
            return True
        current = now or datetime.now(timezone.utc)
        return current - parsed >= timedelta(days=settings.secret_rotation_max_age_days)

    def evaluate(self, *, last_rotated_at: str | None) -> dict:
        due = self.is_rotation_due(last_rotated_at=last_rotated_at)
        return {
            "rotation_due": due,
            "max_age_days": settings.secret_rotation_max_age_days,
            "last_rotated_at": last_rotated_at,
        }
