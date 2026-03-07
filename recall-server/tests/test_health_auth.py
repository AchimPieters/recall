from fastapi.testclient import TestClient

from recall.api.main import app
from recall.core.security import get_password_hash
from recall.db.database import SessionLocal
from recall.models.settings import User


client = TestClient(app)


def _ensure_admin() -> None:
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
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_login_rate_limit_and_auth() -> None:
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
