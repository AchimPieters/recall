from datetime import datetime, timedelta, timezone

from backend.app.services import secret_rotation_service as srs
from backend.app.services.secret_rotation_service import SecretRotationService


def test_rotation_due_when_timestamp_missing(monkeypatch) -> None:
    monkeypatch.setattr(srs.settings, "secret_rotation_max_age_days", 30)
    service = SecretRotationService()
    assert service.is_rotation_due(last_rotated_at=None) is True


def test_rotation_due_when_older_than_threshold(monkeypatch) -> None:
    monkeypatch.setattr(srs.settings, "secret_rotation_max_age_days", 30)
    service = SecretRotationService()
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    assert service.is_rotation_due(last_rotated_at=old) is True


def test_rotation_not_due_when_fresh(monkeypatch) -> None:
    monkeypatch.setattr(srs.settings, "secret_rotation_max_age_days", 30)
    service = SecretRotationService()
    fresh = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    assert service.is_rotation_due(last_rotated_at=fresh) is False


def test_evaluate_payload_shape(monkeypatch) -> None:
    monkeypatch.setattr(srs.settings, "secret_rotation_max_age_days", 45)
    service = SecretRotationService()
    value = datetime.now(timezone.utc).isoformat()
    result = service.evaluate(last_rotated_at=value)
    assert result["max_age_days"] == 45
    assert result["last_rotated_at"] == value
    assert result["rotation_due"] is False
