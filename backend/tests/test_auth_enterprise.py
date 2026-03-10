from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.api.routes import auth as auth_routes
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.repositories.security_repository import SecurityRepository

client = TestClient(app)


def _ensure_user(username: str, password: str, role: str = "viewer", active: bool = True) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash=get_password_hash(password), role=role)
            db.add(user)
        user.password_hash = get_password_hash(password)
        user.role = role
        user.is_active = active
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()
    finally:
        db.close()


def test_logout_revokes_refresh_token() -> None:
    _ensure_user("auth-user", "AuthPass1!", role="admin")

    login = client.post(
        "/api/v1/token",
        data={"username": "auth-user", "password": "AuthPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    refresh = login.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200

    retry = client.post("/api/v1/token/refresh", json={"refresh_token": refresh})
    assert retry.status_code == 401


def test_password_reset_flow_changes_password() -> None:
    _ensure_user("reset-user", "OldPassword1!", role="viewer")

    req = client.post("/api/v1/auth/password-reset/request", json={"username": "reset-user"})
    assert req.status_code == 200
    token = req.json()["reset_token"]

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"reset_token": token, "new_password": "NewPassword1!"},
    )
    assert confirm.status_code == 200

    old_login = client.post(
        "/api/v1/token",
        data={"username": "reset-user", "password": "OldPassword1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/token",
        data={"username": "reset-user", "password": "NewPassword1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert new_login.status_code == 200


def test_admin_can_activate_user() -> None:
    _ensure_user("super-admin", "AdminPass1!", role="admin")
    _ensure_user("target-user", "TargetPass1!", role="viewer", active=False)

    token = create_access_token(subject="super-admin", role="admin")
    activate = client.post(
        "/api/v1/auth/activate",
        json={"username": "target-user", "active": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate.status_code == 200
    assert activate.json()["active"] is True


def test_password_reset_request_hides_token_outside_dev(monkeypatch) -> None:
    _ensure_user("hidden-reset-user", "HiddenReset1!", role="viewer")

    monkeypatch.setattr(auth_routes.settings_conf, "environment", "prod")
    try:
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"username": "hidden-reset-user"},
        )
    finally:
        monkeypatch.setattr(auth_routes.settings_conf, "environment", "dev")

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert "reset_token" not in response.json()


def test_auth_endpoints_emit_audit_logs() -> None:
    _ensure_user("audit-admin", "AdminPass1!", role="admin")
    _ensure_user("audit-reset", "ResetPass1!", role="viewer")

    # password reset request/confirm
    req = client.post("/api/v1/auth/password-reset/request", json={"username": "audit-reset"})
    assert req.status_code == 200
    token = req.json()["reset_token"]

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"reset_token": token, "new_password": "ResetPassUpdated2!"},
    )
    assert confirm.status_code == 200

    # logout writes auth.logout
    login = client.post(
        "/api/v1/token",
        data={"username": "audit-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    refresh = login.json()["refresh_token"]
    out = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 200

    # activate writes auth.activate
    token_admin = create_access_token(subject="audit-admin", role="admin")
    act = client.post(
        "/api/v1/auth/activate",
        json={"username": "audit-reset", "active": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert act.status_code == 200

    db = SessionLocal()
    try:
        repo = SecurityRepository(db)
        assert len(repo.list_audit_logs(actor_id="audit-reset", action="auth.password_reset.request")) >= 1
        assert len(repo.list_audit_logs(actor_id="audit-reset", action="auth.password_reset.confirm")) >= 1
        assert len(repo.list_audit_logs(actor_id="audit-admin", action="auth.logout")) >= 1
        assert len(repo.list_audit_logs(actor_id="audit-admin", action="auth.activate")) >= 1
    finally:
        db.close()
