import pytest

from backend.app.core import security


def test_password_policy_accepts_strong_password(monkeypatch) -> None:
    monkeypatch.setattr(security.settings, "password_min_length", 12)
    monkeypatch.setattr(security.settings, "password_require_upper", True)
    monkeypatch.setattr(security.settings, "password_require_lower", True)
    monkeypatch.setattr(security.settings, "password_require_digit", True)
    monkeypatch.setattr(security.settings, "password_require_symbol", True)

    security.validate_password_policy("Str0ng!Passw0rd")


def test_password_policy_rejects_weak_password(monkeypatch) -> None:
    monkeypatch.setattr(security.settings, "password_min_length", 12)
    monkeypatch.setattr(security.settings, "password_require_upper", True)
    monkeypatch.setattr(security.settings, "password_require_lower", True)
    monkeypatch.setattr(security.settings, "password_require_digit", True)
    monkeypatch.setattr(security.settings, "password_require_symbol", True)

    with pytest.raises(ValueError):
        security.validate_password_policy("weakpass")
