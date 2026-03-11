from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User

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



def test_register_rejects_unsupported_device_protocol_version() -> None:
    _ensure_user("protocol-admin", "AdminPass1!", role="admin")
    token = create_access_token(subject="protocol-admin", role="admin")
    response = client.post(
        "/api/v1/device/register",
        json={"id": "proto-dev-unsupported", "name": "Proto Device", "version": "1.0.0"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Protocol-Version": "2",
        },
    )
    assert response.status_code == 400
    assert "Unsupported device protocol version" in response.json()["detail"]


def test_register_accepts_supported_device_protocol_version() -> None:
    _ensure_user("protocol-admin", "AdminPass1!", role="admin")
    token = create_access_token(subject="protocol-admin", role="admin")
    response = client.post(
        "/api/v1/device/register",
        json={"id": "proto-dev-supported", "name": "Proto Device", "version": "1.0.0"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Protocol-Version": "1",
        },
    )
    assert response.status_code == 200
    assert response.json()["id"] == "proto-dev-supported"


def test_register_accepts_supported_minor_device_protocol_version() -> None:
    _ensure_user("protocol-admin", "AdminPass1!", role="admin")
    token = create_access_token(subject="protocol-admin", role="admin")
    response = client.post(
        "/api/v1/device/register",
        json={"id": "proto-dev-supported-minor", "name": "Proto Device", "version": "1.0.0"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Protocol-Version": "1.2",
        },
    )
    assert response.status_code == 200
    assert response.json()["id"] == "proto-dev-supported-minor"


def test_register_rejects_unsupported_major_device_protocol_version() -> None:
    _ensure_user("protocol-admin", "AdminPass1!", role="admin")
    token = create_access_token(subject="protocol-admin", role="admin")
    response = client.post(
        "/api/v1/device/register",
        json={"id": "proto-dev-unsupported-major", "name": "Proto Device", "version": "1.0.0"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Protocol-Version": "2.0",
        },
    )
    assert response.status_code == 400
    assert "Supported major version: 1.x" in response.json()["detail"]
