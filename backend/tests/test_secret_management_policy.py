import pytest

from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_prod_requires_jwt_secrets_keyring(monkeypatch) -> None:
    monkeypatch.setenv("RECALL_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "prod-single-secret")
    monkeypatch.delenv("JWT_SECRETS", raising=False)

    with pytest.raises(ValueError, match="JWT_SECRETS must be set outside development"):
        get_settings()


def test_prod_uses_first_jwt_secret_from_keyring(monkeypatch) -> None:
    monkeypatch.setenv("RECALL_ENV", "prod")
    monkeypatch.setenv("JWT_SECRETS", "k8s-current,k8s-previous")
    monkeypatch.setenv("RECALL_CLAMAV_FAIL_OPEN", "false")

    settings = get_settings()
    assert settings.jwt_secrets == ["k8s-current", "k8s-previous"]
    assert settings.jwt_secret == "k8s-current"


def test_dev_can_fallback_to_local_default_secret(monkeypatch) -> None:
    monkeypatch.setenv("RECALL_ENV", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRETS", raising=False)

    settings = get_settings()
    assert settings.jwt_secret == "dev-insecure-secret-change-me"


def test_non_dev_disallows_clamav_fail_open(monkeypatch) -> None:
    monkeypatch.setenv("RECALL_ENV", "prod")
    monkeypatch.setenv("JWT_SECRETS", "k8s-current")
    monkeypatch.setenv("RECALL_CLAMAV_FAIL_OPEN", "true")

    with pytest.raises(ValueError, match="RECALL_CLAMAV_FAIL_OPEN must be false"):
        get_settings()
