from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.public_api_auth import reset_public_api_rate_limits_for_tests
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import PublicApiKey, User

client = TestClient(app)


def _ensure_user(username: str, role: str, organization_id: int | None) -> str:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                password_hash=get_password_hash("PublicApiKeyPass1!"),
                role=role,
                organization_id=organization_id,
                is_active=True,
            )
            db.add(user)
        else:
            user.password_hash = get_password_hash("PublicApiKeyPass1!")
            user.role = role
            user.organization_id = organization_id
            user.is_active = True
        db.commit()
    finally:
        db.close()
    return create_access_token(subject=username, role=role)


def _create_public_key(token: str, *, name: str, organization_id: int, rate_limit_per_minute: int) -> tuple[int, str]:
    response = client.post(
        "/api/v1/public-api/keys",
        json={
            "name": name,
            "rate_limit_per_minute": rate_limit_per_minute,
            "organization_id": organization_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    return int(body["id"]), str(body["api_key"])


def test_create_public_api_key_and_authenticate_health() -> None:
    token = _ensure_user("public-key-admin", role="admin", organization_id=1)

    create_resp = client.post(
        "/api/v1/public-api/keys",
        json={"name": "tenant-key", "rate_limit_per_minute": 3, "organization_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()
    assert payload["name"] == "tenant-key"
    raw_key = payload["api_key"]

    health = client.get("/api/public/v1/health", headers={"X-API-Key": raw_key})
    assert health.status_code == 200
    assert health.json()["tenant"] == "org-1"


def test_org_admin_cannot_create_key_for_other_org() -> None:
    token = _ensure_user("public-key-admin2", role="admin", organization_id=2)

    response = client.post(
        "/api/v1/public-api/keys",
        json={"name": "forbidden", "rate_limit_per_minute": 3, "organization_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_disable_public_api_key_blocks_health_access() -> None:
    token = _ensure_user("public-key-admin3", role="admin", organization_id=3)

    create_resp = client.post(
        "/api/v1/public-api/keys",
        json={"name": "tenant-key-3", "rate_limit_per_minute": 3, "organization_id": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    key_id = create_resp.json()["id"]
    raw_key = create_resp.json()["api_key"]

    patch_resp = client.patch(
        f"/api/v1/public-api/keys/{key_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200

    health = client.get("/api/public/v1/health", headers={"X-API-Key": raw_key})
    assert health.status_code == 401

    db = SessionLocal()
    try:
        row = db.query(PublicApiKey).filter(PublicApiKey.id == key_id).first()
        assert row is not None
        assert row.is_active is False
    finally:
        db.close()


def test_db_backed_keys_share_tenant_rate_limit() -> None:
    reset_public_api_rate_limits_for_tests()
    token = _ensure_user("public-key-admin4", role="admin", organization_id=4)

    _, key_one = _create_public_key(token, name="tenant-4-a", organization_id=4, rate_limit_per_minute=2)
    _, key_two = _create_public_key(token, name="tenant-4-b", organization_id=4, rate_limit_per_minute=2)

    first = client.get("/api/public/v1/health", headers={"X-API-Key": key_one})
    second = client.get("/api/public/v1/health", headers={"X-API-Key": key_two})
    third = client.get("/api/public/v1/health", headers={"X-API-Key": key_one})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Public API tenant rate limit exceeded"


def test_db_backed_keys_are_rate_limited_per_tenant() -> None:
    reset_public_api_rate_limits_for_tests()
    token_org_5 = _ensure_user("public-key-admin5", role="admin", organization_id=5)
    token_org_6 = _ensure_user("public-key-admin6", role="admin", organization_id=6)

    _, key_org_5 = _create_public_key(token_org_5, name="tenant-5", organization_id=5, rate_limit_per_minute=1)
    _, key_org_6 = _create_public_key(token_org_6, name="tenant-6", organization_id=6, rate_limit_per_minute=1)

    org5_first = client.get("/api/public/v1/health", headers={"X-API-Key": key_org_5})
    org6_first = client.get("/api/public/v1/health", headers={"X-API-Key": key_org_6})
    org5_second = client.get("/api/public/v1/health", headers={"X-API-Key": key_org_5})

    assert org5_first.status_code == 200
    assert org6_first.status_code == 200
    assert org6_first.json()["tenant"] == "org-6"
    assert org5_second.status_code == 429


def test_list_public_api_keys_is_tenant_scoped() -> None:
    token_org_7 = _ensure_user("public-key-admin7", role="admin", organization_id=7)
    token_org_8 = _ensure_user("public-key-admin8", role="admin", organization_id=8)

    _create_public_key(token_org_7, name="org7-key", organization_id=7, rate_limit_per_minute=5)
    _create_public_key(token_org_8, name="org8-key", organization_id=8, rate_limit_per_minute=5)

    response = client.get(
        "/api/v1/public-api/keys",
        headers={"Authorization": f"Bearer {token_org_7}"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert any(row["name"] == "org7-key" for row in rows)
    assert not any(row["name"] == "org8-key" for row in rows)


def test_org_admin_cannot_update_key_from_other_org() -> None:
    token_org_9 = _ensure_user("public-key-admin9", role="admin", organization_id=9)
    token_org_10 = _ensure_user("public-key-admin10", role="admin", organization_id=10)

    key_id, _ = _create_public_key(token_org_10, name="org10-key", organization_id=10, rate_limit_per_minute=5)

    patch_response = client.patch(
        f"/api/v1/public-api/keys/{key_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token_org_9}"},
    )

    assert patch_response.status_code == 403
    assert patch_response.json()["detail"] == "Cross-organization key update denied"


def test_superadmin_lists_keys_across_organizations() -> None:
    super_token = _ensure_user("public-key-superadmin", role="superadmin", organization_id=None)
    token_org_11 = _ensure_user("public-key-admin11", role="admin", organization_id=11)
    token_org_12 = _ensure_user("public-key-admin12", role="admin", organization_id=12)

    _create_public_key(token_org_11, name="org11-key", organization_id=11, rate_limit_per_minute=5)
    _create_public_key(token_org_12, name="org12-key", organization_id=12, rate_limit_per_minute=5)

    list_response = client.get(
        "/api/v1/public-api/keys",
        headers={"Authorization": f"Bearer {super_token}"},
    )

    assert list_response.status_code == 200
    names = {row["name"] for row in list_response.json()}
    assert "org11-key" in names
    assert "org12-key" in names


def test_superadmin_can_disable_other_org_key() -> None:
    super_token = _ensure_user("public-key-superadmin2", role="superadmin", organization_id=None)
    token_org_13 = _ensure_user("public-key-admin13", role="admin", organization_id=13)

    key_id, raw_key = _create_public_key(token_org_13, name="org13-key", organization_id=13, rate_limit_per_minute=5)

    patch_response = client.patch(
        f"/api/v1/public-api/keys/{key_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {super_token}"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["is_active"] is False

    health = client.get("/api/public/v1/health", headers={"X-API-Key": raw_key})
    assert health.status_code == 401
