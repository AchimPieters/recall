from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.api.routes import auth as auth_routes
from backend.app.core.mfa import generate_totp_code
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.repositories.security_repository import SecurityRepository

client = TestClient(app)


def _ensure_user(
    username: str, password: str, role: str = "viewer", active: bool = True
) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username, password_hash=get_password_hash(password), role=role
            )
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
    _ensure_user("auth-user", "AuthPass1!", role="viewer")

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

    req = client.post(
        "/api/v1/auth/password-reset/request", json={"username": "reset-user"}
    )
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
    _ensure_user("audit-user", "UserPass1!", role="viewer")
    _ensure_user("audit-reset", "ResetPass1!", role="viewer")

    # password reset request/confirm
    req = client.post(
        "/api/v1/auth/password-reset/request", json={"username": "audit-reset"}
    )
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
        data={"username": "audit-user", "password": "UserPass1!"},
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

    # mfa setup/enable/verify writes auth.mfa.* actions
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": generate_totp_code(secret)},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert enable.status_code == 200

    login_admin = client.post(
        "/api/v1/token",
        data={"username": "audit-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_admin.status_code == 200
    mfa_token = login_admin.json()["mfa_token"]

    verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": generate_totp_code(secret)},
    )
    assert verify.status_code == 200

    db = SessionLocal()
    try:
        repo = SecurityRepository(db)
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="audit-reset", action="auth.password_reset.request"
                )
            )
            >= 1
        )
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="audit-reset", action="auth.password_reset.confirm"
                )
            )
            >= 1
        )
        assert (
            len(repo.list_audit_logs(actor_id="audit-user", action="auth.logout")) >= 1
        )
        assert (
            len(repo.list_audit_logs(actor_id="audit-admin", action="auth.activate"))
            >= 1
        )
        assert (
            len(repo.list_audit_logs(actor_id="audit-admin", action="auth.mfa.setup"))
            >= 1
        )
        assert (
            len(repo.list_audit_logs(actor_id="audit-admin", action="auth.mfa.enable"))
            >= 1
        )
        assert (
            len(repo.list_audit_logs(actor_id="audit-admin", action="auth.mfa.verify"))
            >= 1
        )
    finally:
        db.close()


def test_admin_login_requires_mfa_and_verify_flow() -> None:
    _ensure_user("mfa-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": generate_totp_code(secret)},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert enable.status_code == 200
    assert enable.json()["status"] == "mfa_enabled"

    login = client.post(
        "/api/v1/token",
        data={"username": "mfa-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    assert login.json()["mfa_required"] is True
    mfa_token = login.json()["mfa_token"]

    verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": generate_totp_code(secret)},
    )
    assert verify.status_code == 200
    assert "access_token" in verify.json()
    assert "refresh_token" in verify.json()


def test_admin_without_mfa_is_blocked() -> None:
    _ensure_user("blocked-admin", "AdminPass1!", role="admin")

    login = client.post(
        "/api/v1/token",
        data={"username": "blocked-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 403
    assert "MFA setup required" in login.json()["detail"]


def test_mfa_verify_lockout_after_repeated_failures(monkeypatch) -> None:
    _ensure_user("mfa-lock-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-lock-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": generate_totp_code(secret)},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert enable.status_code == 200

    login = client.post(
        "/api/v1/token",
        data={"username": "mfa-lock-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    mfa_token = login.json()["mfa_token"]

    monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 2)
    try:
        first = client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": "000000"},
        )
        second = client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": "111111"},
        )
        third = client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": "222222"},
        )
    finally:
        monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 5)

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert "MFA temporarily locked" in third.json()["detail"]

    db = SessionLocal()
    try:
        repo = SecurityRepository(db)
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="mfa-lock-admin", action="auth.mfa.verify.failed"
                )
            )
            >= 2
        )
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="mfa-lock-admin", action="auth.mfa.verify.locked"
                )
            )
            >= 1
        )
    finally:
        db.close()


def test_mfa_verify_requires_exactly_one_factor() -> None:
    _ensure_user("mfa-factor-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-factor-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    recovery_code = setup.json()["recovery_codes"][0]

    enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": generate_totp_code(secret)},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert enable.status_code == 200

    login = client.post(
        "/api/v1/token",
        data={"username": "mfa-factor-admin", "password": "AdminPass1!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    mfa_token = login.json()["mfa_token"]

    none_factor = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token},
    )
    both_factors = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "mfa_token": mfa_token,
            "code": generate_totp_code(secret),
            "recovery_code": recovery_code,
        },
    )

    assert none_factor.status_code == 400
    assert "Either code or recovery_code is required" in none_factor.json()["detail"]
    assert both_factors.status_code == 400
    assert "Provide either code or recovery_code" in both_factors.json()["detail"]


def test_mfa_setup_invalid_code_emits_audit_log() -> None:
    _ensure_user("mfa-enable-fail-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-enable-fail-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200

    failed_enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert failed_enable.status_code == 401

    db = SessionLocal()
    try:
        repo = SecurityRepository(db)
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="mfa-enable-fail-admin", action="auth.mfa.enable.failed"
                )
            )
            >= 1
        )
    finally:
        db.close()


def test_mfa_setup_lockout_after_repeated_enable_failures(monkeypatch) -> None:
    _ensure_user("mfa-setup-lock-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-setup-lock-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200

    monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 2)
    try:
        first = client.post(
            "/api/v1/auth/mfa/setup",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        second = client.post(
            "/api/v1/auth/mfa/setup",
            json={"code": "111111"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        third = client.post(
            "/api/v1/auth/mfa/setup",
            json={"code": "222222"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
    finally:
        monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 5)

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert "MFA setup temporarily locked" in third.json()["detail"]

    db = SessionLocal()
    try:
        repo = SecurityRepository(db)
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="mfa-setup-lock-admin", action="auth.mfa.enable.failed"
                )
            )
            >= 2
        )
        assert (
            len(
                repo.list_audit_logs(
                    actor_id="mfa-setup-lock-admin", action="auth.mfa.enable.locked"
                )
            )
            >= 1
        )
    finally:
        db.close()


def test_mfa_setup_lockout_does_not_lock_verify_flow(monkeypatch) -> None:
    _ensure_user("mfa-lock-scope-admin", "AdminPass1!", role="admin")
    token_admin = create_access_token(subject="mfa-lock-scope-admin", role="admin")

    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"regenerate": True},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enable = client.post(
        "/api/v1/auth/mfa/setup",
        json={"code": generate_totp_code(secret)},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert enable.status_code == 200

    monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 1)
    try:
        failed_enable = client.post(
            "/api/v1/auth/mfa/setup",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        locked_enable = client.post(
            "/api/v1/auth/mfa/setup",
            json={"code": "111111"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        login = client.post(
            "/api/v1/token",
            data={"username": "mfa-lock-scope-admin", "password": "AdminPass1!"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200
        mfa_token = login.json()["mfa_token"]

        verify = client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": generate_totp_code(secret)},
        )
    finally:
        monkeypatch.setattr(auth_routes.settings_conf, "auth_lockout_threshold", 5)

    assert failed_enable.status_code == 401
    assert locked_enable.status_code == 429
    assert verify.status_code == 200


def test_refresh_token_blocked_for_admin_without_mfa() -> None:
    _ensure_user("refresh-mfa-admin", "AdminPass1!", role="admin")

    # Seed a refresh token directly to simulate pre-existing token during policy hardening.
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "refresh-mfa-admin").first()
        assert user is not None
        user.mfa_enabled = False
        user.mfa_secret = None
        db.commit()
    finally:
        db.close()

    from backend.app.core.security import create_refresh_token, hash_token

    refresh, jti = create_refresh_token(subject="refresh-mfa-admin")
    db = SessionLocal()
    try:
        SecurityRepository(db).create_refresh_token(
            "refresh-mfa-admin",
            hash_token(jti),
            auth_routes.datetime.now(auth_routes.timezone.utc)
            + auth_routes.timedelta(minutes=30),
        )
        db.commit()
    finally:
        db.close()

    response = client.post("/api/v1/token/refresh", json={"refresh_token": refresh})
    assert response.status_code == 403
    assert response.json()["detail"] == "MFA required for admin account"


def test_refresh_token_blocked_for_inactive_user() -> None:
    _ensure_user("refresh-inactive-user", "UserPass1!", role="viewer", active=False)

    from backend.app.core.security import create_refresh_token, hash_token

    refresh, jti = create_refresh_token(subject="refresh-inactive-user")
    db = SessionLocal()
    try:
        SecurityRepository(db).create_refresh_token(
            "refresh-inactive-user",
            hash_token(jti),
            auth_routes.datetime.now(auth_routes.timezone.utc)
            + auth_routes.timedelta(minutes=30),
        )
        db.commit()
    finally:
        db.close()

    response = client.post("/api/v1/token/refresh", json={"refresh_token": refresh})
    assert response.status_code == 403
    assert response.json()["detail"] == "Account inactive"
