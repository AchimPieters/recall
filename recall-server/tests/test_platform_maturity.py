from fastapi.testclient import TestClient

from recall.api.main import app
from recall.core.security import create_access_token, get_password_hash
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
