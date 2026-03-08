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


def test_refresh_token_flow_rotates_token() -> None:
    _reset_login_state()
    _ensure_admin()
    response = client.post(
        "/token",
        data={"username": "admin", "password": "admin"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "refresh_token" in payload

    refreshed = client.post(
        "/token/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert refreshed.status_code == 200
    refreshed_json = refreshed.json()
    assert refreshed_json["access_token"]
    assert refreshed_json["refresh_token"] != payload["refresh_token"]


def test_permission_enforcement_blocks_viewer_write() -> None:
    _reset_login_state()
    _ensure_admin()
    db = SessionLocal()
    try:
        viewer = db.query(User).filter(User.username == "viewer").first()
        if not viewer:
            viewer = User(
                username="viewer",
                password_hash=get_password_hash("viewer"),
                role="viewer",
            )
            db.add(viewer)
        else:
            viewer.password_hash = get_password_hash("viewer")
            viewer.role = "viewer"
        db.commit()
    finally:
        db.close()

    token = create_access_token(subject="viewer", role="viewer")
    blocked = client.post(
        "/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("x.txt", b"data", "text/plain")},
    )
    assert blocked.status_code == 403


def test_security_audit_endpoint_admin_only() -> None:
    _reset_login_state()
    _ensure_admin()

    login = client.post(
        "/token",
        data={"username": "admin", "password": "admin"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    admin_token = login.json()["access_token"]

    events = client.get(
        "/security/audit?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert events.status_code == 200
    payload = events.json()
    assert isinstance(payload, list)
    assert payload
    assert {"actor", "event_type", "detail"}.issubset(payload[0].keys())

    db = SessionLocal()
    try:
        viewer = db.query(User).filter(User.username == "viewer2").first()
        if not viewer:
            viewer = User(
                username="viewer2",
                password_hash=get_password_hash("viewer2"),
                role="viewer",
            )
            db.add(viewer)
        else:
            viewer.password_hash = get_password_hash("viewer2")
            viewer.role = "viewer"
        db.commit()
    finally:
        db.close()

    viewer_login = client.post(
        "/token",
        data={"username": "viewer2", "password": "viewer2"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert viewer_login.status_code == 200
    viewer_token = viewer_login.json()["access_token"]

    denied = client.get(
        "/security/audit",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert denied.status_code == 403


def test_refresh_failure_is_audited() -> None:
    _reset_login_state()
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")

    bad = client.post("/token/refresh", json={"refresh_token": "invalid-token"})
    assert bad.status_code == 401

    events = client.get(
        "/security/audit?event_type=token_refresh_failed&limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    payload = events.json()
    assert payload
    assert payload[0]["event_type"] == "token_refresh_failed"


def test_auth_alias_endpoints_work() -> None:
    _reset_login_state()
    _ensure_admin()
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    payload = response.json()
    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert refreshed.status_code == 200


def test_audit_logs_alias_endpoint_admin_only() -> None:
    _reset_login_state()
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    ok = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
