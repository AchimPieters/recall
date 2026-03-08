from fastapi.testclient import TestClient

from recall.api.main import app
from recall.core.security import create_access_token, get_password_hash, verify_password
from recall.db.database import Base, SessionLocal, engine
from recall.models.settings import User

client = TestClient(app)


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


def test_liveness_and_request_id_headers() -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"
    assert response.headers["x-request-id"]


def test_groups_alerts_layouts_and_screenshots() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.post(
        "/device/register", headers=headers, json={"id": "dev-2", "name": "Lobby"}
    )
    assert reg.status_code == 200

    group = client.post("/device/groups", headers=headers, json={"name": "Floor-1"})
    assert group.status_code == 200
    group_id = group.json()["id"]

    member = client.post(
        f"/device/groups/{group_id}/members",
        headers=headers,
        json={"device_id": "dev-2"},
    )
    assert member.status_code == 200

    shot = client.post(
        "/device/screenshot",
        headers=headers,
        json={"id": "dev-2", "image_path": "/tmp/dev-2.png"},
    )
    assert shot.status_code == 200

    layout = client.post(
        "/playlists/layouts",
        headers=headers,
        json={"name": "2-zone", "definition_json": '{"zones":[{"id":"left"}]}'},
    )
    assert layout.status_code == 200

    alert = client.post(
        "/monitor/alerts",
        headers=headers,
        json={"level": "warning", "source": "device", "message": "device lag"},
    )
    assert alert.status_code == 200
    alert_id = alert.json()["id"]

    resolved = client.post(f"/monitor/alerts/{alert_id}/resolve", headers=headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_settings_schema_and_event_stream() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    bad = client.post("/settings", headers=headers, json={"unknown_key": "x"})
    assert bad.status_code == 422

    applied = client.post(
        "/settings/apply?confirmed=true",
        headers=headers,
        json={"site_name": "Recall HQ", "timezone": "Europe/Amsterdam"},
    )
    assert applied.status_code == 200

    events = client.get("/events", headers=headers)
    assert events.status_code == 200
    assert any(event["action"] == "settings_apply" for event in events.json())


def test_device_group_bulk_actions_create_events_and_logs() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.post(
        "/device/register", headers=headers, json={"id": "dev-bulk-1", "name": "Atrium"}
    )
    assert reg.status_code == 200

    group = client.post("/device/groups", headers=headers, json={"name": "Bulk Ops"})
    assert group.status_code == 200
    group_id = group.json()["id"]

    member = client.post(
        f"/device/groups/{group_id}/members",
        headers=headers,
        json={"device_id": "dev-bulk-1"},
    )
    assert member.status_code == 200

    reboot = client.post(
        f"/device/groups/{group_id}/bulk",
        headers=headers,
        json={"action": "reboot"},
    )
    assert reboot.status_code == 200
    body = reboot.json()
    assert body["action"] == "reboot"
    assert body["accepted"] == 1
    assert body["device_ids"] == ["dev-bulk-1"]

    update = client.post(
        f"/device/groups/{group_id}/bulk",
        headers=headers,
        json={"action": "update", "target_version": "2.0.1"},
    )
    assert update.status_code == 200
    assert update.json()["target_version"] == "2.0.1"

    events = client.get("/events?limit=20", headers=headers)
    assert events.status_code == 200
    actions = [e["action"] for e in events.json()]
    assert "bulk_reboot" in actions
    assert "bulk_update" in actions

    logs = client.get("/device/logs?limit=20", headers=headers)
    assert logs.status_code == 200
    log_actions = [entry["action"] for entry in logs.json()]
    assert "bulk_reboot" in log_actions
    assert "bulk_update" in log_actions


def test_stale_device_status_without_heartbeat() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.post(
        "/device/register", headers=headers, json={"id": "dev-stale", "name": "Hall"}
    )
    assert reg.status_code == 200

    from recall.db.database import SessionLocal
    from recall.models.device import Device

    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == "dev-stale").first()
        assert device is not None
        device.last_seen = None
        db.commit()
    finally:
        db.close()

    listed = client.get("/device/list", headers=headers)
    assert listed.status_code == 200
    target = [d for d in listed.json() if d["id"] == "dev-stale"][0]
    assert target["status"] == "stale"


def test_password_hash_uses_argon2() -> None:
    hashed = get_password_hash("s3cret")
    assert hashed.startswith("$argon2")
    assert verify_password("s3cret", hashed)


def test_zone_table_registered_in_metadata() -> None:
    Base.metadata.create_all(bind=engine)
    assert "zones" in Base.metadata.tables


def test_device_group_rollback_requires_target_version() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/device/register", headers=headers, json={"id": "dev-roll-1", "name": "Store"}
    )
    group = client.post(
        "/device/groups", headers=headers, json={"name": "Rollback Ops"}
    )
    group_id = group.json()["id"]
    client.post(
        f"/device/groups/{group_id}/members",
        headers=headers,
        json={"device_id": "dev-roll-1"},
    )

    missing = client.post(
        f"/device/groups/{group_id}/bulk",
        headers=headers,
        json={"action": "rollback"},
    )
    assert missing.status_code == 400
    assert "target_version" in missing.json()["detail"]


def test_device_group_rollback_logs_event() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/device/register", headers=headers, json={"id": "dev-roll-2", "name": "Hall"}
    )
    group = client.post(
        "/device/groups", headers=headers, json={"name": "Rollback Ops 2"}
    )
    group_id = group.json()["id"]
    client.post(
        f"/device/groups/{group_id}/members",
        headers=headers,
        json={"device_id": "dev-roll-2"},
    )

    rollback = client.post(
        f"/device/groups/{group_id}/bulk",
        headers=headers,
        json={"action": "rollback", "target_version": "2.0.0"},
    )
    assert rollback.status_code == 200
    body = rollback.json()
    assert body["action"] == "rollback"
    assert body["target_version"] == "2.0.0"

    events = client.get("/events?limit=20", headers=headers)
    assert events.status_code == 200
    actions = [e["action"] for e in events.json()]
    assert "bulk_rollback" in actions
