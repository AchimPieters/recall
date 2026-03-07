from datetime import datetime, timedelta, timezone

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


def test_playlist_schedule_and_device_config_resolution() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/playlists", headers=headers, json={"name": "Main loop"})
    assert created.status_code == 200
    playlist_id = created.json()["id"]

    starts_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    ends_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    scheduled = client.post(
        f"/playlists/{playlist_id}/schedule",
        headers=headers,
        json={"target": "all", "starts_at": starts_at, "ends_at": ends_at},
    )
    assert scheduled.status_code == 200

    config = client.get(
        "/device/config", headers=headers, params={"device_id": "dev-1"}
    )
    assert config.status_code == 200
    assert config.json()["active_playlist_id"] == playlist_id


def test_schedule_rejects_invalid_window() -> None:
    _ensure_admin()
    token = create_access_token(subject="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/playlists", headers=headers, json={"name": "Window"})
    playlist_id = created.json()["id"]

    now = datetime.now(timezone.utc)
    response = client.post(
        f"/playlists/{playlist_id}/schedule",
        headers=headers,
        json={
            "target": "all",
            "starts_at": now.isoformat(),
            "ends_at": (now - timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 400
