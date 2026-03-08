from fastapi.testclient import TestClient

from recall.api.main import app, failed_login_attempts
from recall.core.config import get_settings
from recall.core.security import create_access_token, get_password_hash
from recall.db.database import Base, SessionLocal, engine
from recall.models.settings import User


client = TestClient(app)


def _reset_login_state() -> None:
    failed_login_attempts.clear()


def _ensure_admin() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin", password_hash=get_password_hash("admin"), role="admin"
            )
            db.add(admin)
        else:
            admin.password_hash = get_password_hash("admin")
            admin.role = "admin"
        db.commit()
    finally:
        db.close()


def test_health_and_ready_endpoints() -> None:
    _reset_login_state()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert client.get("/ready").status_code == 200


def test_login_rate_limit_and_auth() -> None:
    _reset_login_state()
    _ensure_admin()
    response = client.post(
        "/token",
        data={"username": "admin", "password": "admin"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    devices = client.get("/device/list", headers={"Authorization": f"Bearer {token}"})
    assert devices.status_code == 200


def test_role_is_loaded_from_database_not_token_claim() -> None:
    _reset_login_state()
    _ensure_admin()
    token = create_access_token(subject="admin", role="viewer")

    # Should still be authorized as admin because role is read from DB, not claim.
    response = client.post(
        "/system/reboot?confirmed=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["reason"] == "confirmation_required"


def test_settings_reject_unknown_keys() -> None:
    _reset_login_state()
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    response = client.post(
        "/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"unknown_key": "value"},
    )
    assert response.status_code == 422


def test_version_endpoint() -> None:
    _reset_login_state()
    response = client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "environment" in payload


def test_account_lockout_after_failed_logins() -> None:
    _reset_login_state()
    _ensure_admin()
    settings = get_settings()

    for _ in range(settings.auth_lockout_threshold):
        failed = client.post(
            "/token",
            data={"username": "admin", "password": "wrong"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert failed.status_code == 401

    locked = client.post(
        "/token",
        data={"username": "admin", "password": "admin"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert locked.status_code == 429
