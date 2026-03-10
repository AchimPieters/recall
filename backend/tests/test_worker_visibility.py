from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User
from backend.app.workers import celery_app as celery_module

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


class _InspectOK:
    def stats(self):
        return {"worker@node": {}}

    def active(self):
        return {"worker@node": [{"id": "a1"}]}

    def scheduled(self):
        return {"worker@node": []}

    def reserved(self):
        return {"worker@node": [{"id": "r1"}, {"id": "r2"}]}


class _InspectFail:
    def stats(self):
        raise RuntimeError("inspect unavailable")

    def active(self):
        return {}

    def scheduled(self):
        return {}

    def reserved(self):
        return {}


def test_worker_snapshot_reports_counts(monkeypatch) -> None:
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    snapshot = celery_module.get_worker_snapshot()
    assert snapshot["available"] is True
    assert snapshot["workers"]["worker@node"]["active"] == 1
    assert snapshot["workers"]["worker@node"]["reserved"] == 2


def test_worker_snapshot_handles_inspect_failure(monkeypatch) -> None:
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectFail())

    snapshot = celery_module.get_worker_snapshot()
    assert snapshot["available"] is False
    assert "inspect unavailable" in snapshot["error"]


def test_workers_status_route_requires_auth_and_returns_snapshot(monkeypatch) -> None:
    _ensure_user("worker-admin", "AdminPass1!", role="admin")
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    token = create_access_token(subject="worker-admin", role="admin")
    response = client.get(
        "/api/v1/workers/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["workers"]["worker@node"]["active"] == 1
