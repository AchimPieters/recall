from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User


client = TestClient(app)


def _ensure_user(username: str, role: str = "admin") -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash="x", role=role)
            db.add(user)
            db.commit()
    finally:
        db.close()


def test_provisioning_token_and_enroll_flow() -> None:
    _ensure_user("prov-admin", role="admin")
    token = create_access_token(subject="prov-admin", role="admin")

    create_resp = client.post(
        "/api/v1/device/provisioning/token",
        json={"expires_in_minutes": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    provisioning_token = create_resp.json()["token"]

    enroll = client.post(
        "/api/v1/device/provision/enroll",
        json={
            "provisioning_token": provisioning_token,
            "id": "provisioned-device-1",
            "name": "Provisioned Device",
            "version": "1.2.3",
        },
        headers={"X-Device-Protocol-Version": "1"},
    )
    assert enroll.status_code == 200
    assert enroll.json()["device_id"] == "provisioned-device-1"
    assert "certificate" in enroll.json()


def test_provisioning_token_single_use() -> None:
    _ensure_user("prov-admin-2", role="admin")
    token = create_access_token(subject="prov-admin-2", role="admin")

    create_resp = client.post(
        "/api/v1/device/provisioning/token",
        json={"expires_in_minutes": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    provisioning_token = create_resp.json()["token"]

    payload = {
        "provisioning_token": provisioning_token,
        "id": "provisioned-device-2",
        "name": "Provisioned Device 2",
    }
    first = client.post("/api/v1/device/provision/enroll", json=payload)
    assert first.status_code == 200

    second = client.post(
        "/api/v1/device/provision/enroll",
        json={**payload, "id": "provisioned-device-3"},
    )
    assert second.status_code == 400
    assert "invalid or expired provisioning token" in second.json()["detail"]
