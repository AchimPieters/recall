from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import Device, DeviceLog, Event, User

client = TestClient(app)


def _seed_user() -> str:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "analytics-admin").first()
        if not user:
            user = User(username="analytics-admin", password_hash="x", role="admin", organization_id=1, is_active=True)
            db.add(user)
        else:
            user.role = "admin"
            user.organization_id = 1
            user.is_active = True
        db.commit()
    finally:
        db.close()
    return create_access_token(subject="analytics-admin", role="admin")


def _seed_data() -> None:
    db = SessionLocal()
    try:
        db.query(DeviceLog).delete()
        db.query(Event).delete()
        db.query(Device).delete()

        online = Device(id="a-1", name="A1", status="online", organization_id=1)
        offline = Device(id="a-2", name="A2", status="offline", organization_id=1)
        foreign = Device(id="a-3", name="A3", status="online", organization_id=2)
        db.add_all([online, offline, foreign])

        db.add(Event(category="playback", action="impression", actor="agent", payload="{}", organization_id=1))
        db.add(Event(category="playback", action="impression", actor="agent", payload="{}", organization_id=2))

        now = datetime.now(timezone.utc)
        db.add(DeviceLog(device_id="a-1", level="error", action="playback", message="err", timestamp=now - timedelta(hours=1)))
        db.add(DeviceLog(device_id="a-1", level="info", action="heartbeat", message="ok", timestamp=now - timedelta(hours=2)))
        db.add(DeviceLog(device_id="a-3", level="error", action="playback", message="foreign", timestamp=now - timedelta(hours=1)))
        db.commit()
    finally:
        db.close()


def test_analytics_summary_filters_by_tenant() -> None:
    token = _seed_user()
    _seed_data()

    response = client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_devices"] == 2
    assert payload["device_uptime_percent"] == 50.0
    assert payload["content_impressions"] == 1
    assert payload["playback_errors_24h"] == 1
    assert payload["screen_activity_24h"] == 2
