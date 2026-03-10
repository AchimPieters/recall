from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.services.device_service import DeviceService

client = TestClient(app)


def _ensure_user(username: str, password: str, role: str = "admin") -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash=get_password_hash(password), role=role)
            db.add(user)
        user.password_hash = get_password_hash(password)
        user.role = role
        user.is_active = True
        db.commit()
    finally:
        db.close()


def _auth_headers(username: str, role: str = "admin") -> dict[str, str]:
    token = create_access_token(subject=username, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_list_devices_rejects_invalid_status_filter() -> None:
    _ensure_user("fleet-admin", "AdminPass1!", role="admin")

    response = client.get(
        "/api/v1/device/list",
        params={"status": "unknown"},
        headers=_auth_headers("fleet-admin"),
    )

    assert response.status_code == 400
    assert "invalid status" in response.json()["detail"]


def test_list_devices_rejects_invalid_last_seen_before() -> None:
    _ensure_user("fleet-admin", "AdminPass1!", role="admin")

    response = client.get(
        "/api/v1/device/list",
        params={"last_seen_before": "not-a-timestamp"},
        headers=_auth_headers("fleet-admin"),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid last_seen_before timestamp"


def test_list_devices_accepts_zulu_timestamp() -> None:
    _ensure_user("fleet-admin", "AdminPass1!", role="admin")

    db = SessionLocal()
    try:
        DeviceService(db).register("fleet-dev-1", "Fleet Device", None, "1.0.0", organization_id=None)
    finally:
        db.close()

    response = client.get(
        "/api/v1/device/list",
        params={"last_seen_before": "2099-01-01T00:00:00Z"},
        headers=_auth_headers("fleet-admin"),
    )

    assert response.status_code == 200
    assert any(device["id"] == "fleet-dev-1" for device in response.json())


def test_group_bulk_action_supports_staged_dry_run() -> None:
    _ensure_user("fleet-admin", "AdminPass1!", role="admin")

    db = SessionLocal()
    try:
        svc = DeviceService(db)
        svc.register("bulk-1", "Bulk 1", None, "1.1.0", organization_id=None)
        svc.register("bulk-2", "Bulk 2", None, "1.1.0", organization_id=None)
        group = svc.create_group("BulkGroup", organization_id=None)
        group_id = group.id
        svc.assign_group_member(group_id, "bulk-1")
        svc.assign_group_member(group_id, "bulk-2")
    finally:
        db.close()

    response = client.post(
        f"/api/v1/device/groups/{group_id}/bulk",
        json={
            "action": "update",
            "target_version": "1.2.0",
            "rollout_percentage": 50,
            "dry_run": True,
        },
        headers=_auth_headers("fleet-admin"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["accepted"] == 1
    assert len(body["deferred_device_ids"]) == 1


def test_export_devices_csv_returns_csv_payload() -> None:
    _ensure_user("fleet-export-admin", "AdminPass1!", role="admin")

    db = SessionLocal()
    try:
        DeviceService(db).register("csv-dev-1", "CSV Device", None, "1.0.0", organization_id=None)
    finally:
        db.close()

    response = client.get(
        "/api/v1/device/export.csv",
        headers=_auth_headers("fleet-export-admin"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"devices.csv\"" == response.headers["content-disposition"]
    lines = response.text.splitlines()
    assert lines[0] == "id,name,status,version,last_seen,organization_id"
    assert any(line.startswith("csv-dev-1,CSV Device,") for line in lines[1:])
