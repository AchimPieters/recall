from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.services.device_service import DeviceService

client = TestClient(app)


def _db_session():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    return Session()


def _ensure_user(username: str, password: str, role: str = "admin") -> None:
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
        user.is_active = True
        db.commit()
    finally:
        db.close()


def _auth(username: str, role: str = "admin") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(subject=username, role=role)}"
    }


def test_alert_level_and_status_validation_in_service() -> None:
    db = _db_session()
    svc = DeviceService(db)

    alert = svc.create_alert(
        "Warning", "system", "disk usage high", organization_id=None
    )
    assert alert.level == "warning"

    try:
        svc.create_alert("urgent", "system", "bad", organization_id=None)
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        svc.list_alerts(status="invalid", organization_id=None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_alert_ack_and_resolve_route_flow() -> None:
    _ensure_user("monitor-admin", "AdminPass1!", role="admin")
    headers = _auth("monitor-admin")

    created = client.post(
        "/api/v1/monitor/alerts",
        json={"level": "critical", "source": "agent", "message": "playback failed"},
        headers=headers,
    )
    assert created.status_code == 200
    alert_id = created.json()["id"]

    ack = client.post(f"/api/v1/monitor/alerts/{alert_id}/ack", headers=headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"

    resolved = client.post(
        f"/api/v1/monitor/alerts/{alert_id}/resolve", headers=headers
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_alert_routes_reject_invalid_inputs() -> None:
    _ensure_user("monitor-admin", "AdminPass1!", role="admin")
    headers = _auth("monitor-admin")

    bad_level = client.post(
        "/api/v1/monitor/alerts",
        json={"level": "urgent", "source": "agent", "message": "x"},
        headers=headers,
    )
    assert bad_level.status_code == 400
    assert "unsupported alert level" in bad_level.json()["detail"]

    bad_status = client.get(
        "/api/v1/monitor/alerts", params={"status": "broken"}, headers=headers
    )
    assert bad_status.status_code == 400
    assert "unsupported alert status" in bad_status.json()["detail"]
