from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import Alert, Device, User
from backend.app.services.device_service import DeviceService
from backend.app.workers import celery_app as celery_module

client = TestClient(app)


def _ensure_user(username: str, password: str, role: str = "admin", organization_id: int | None = None) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash=get_password_hash(password), role=role)
            db.add(user)
        user.password_hash = get_password_hash(password)
        user.role = role
        user.organization_id = organization_id
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
        return {"worker@node": []}


def test_observability_summary_requires_auth() -> None:
    response = client.get("/api/v1/observability/summary")
    assert response.status_code == 401


def test_observability_summary_returns_devices_alerts_and_workers(monkeypatch) -> None:
    _ensure_user("obs-admin", "AdminPass1!", role="admin")
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    db = SessionLocal()
    try:
        svc = DeviceService(db)
        svc.register("obs-dev-1", "Obs Device 1", None, "1.0.0", organization_id=None)
        svc.register("obs-dev-2", "Obs Device 2", None, "1.0.0", organization_id=None)
        db.add(Alert(organization_id=None, level="warning", source="system", message="a1", status="open"))
        db.add(Alert(organization_id=None, level="warning", source="system", message="a2", status="resolved"))
        db.commit()
    finally:
        db.close()

    token = create_access_token(subject="obs-admin", role="admin")
    response = client.get(
        "/api/v1/observability/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["devices"]["total"] >= 2
    assert body["alerts"]["total"] >= 2
    assert body["alerts"]["open"] >= 1
    assert body["alerts"]["resolved"] >= 1
    assert body["workers"]["available"] is True


def test_observability_summary_is_tenant_scoped_for_org_user(monkeypatch) -> None:
    tenant_org_id = 7007
    other_org_id = 7008
    _ensure_user("obs-operator", "OperatorPass1!", role="operator", organization_id=tenant_org_id)
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    db = SessionLocal()
    try:
        svc = DeviceService(db)
        before_tenant_device_count = db.query(Device).filter(Device.organization_id == tenant_org_id).count()
        before_tenant_alert_count = db.query(Alert).filter(Alert.organization_id == tenant_org_id).count()

        svc.register("obs-org-1-7007", "Org Device", None, "1.0.0", organization_id=tenant_org_id)
        svc.register("obs-org-2-7008", "Other Org Device", None, "1.0.0", organization_id=other_org_id)
        db.add(Alert(organization_id=tenant_org_id, level="warning", source="system", message="org7-open", status="open"))
        db.add(Alert(organization_id=other_org_id, level="warning", source="system", message="org8-open", status="open"))
        db.commit()
    finally:
        db.close()

    token = create_access_token(subject="obs-operator", role="operator")
    response = client.get(
        "/api/v1/observability/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["devices"]["total"] >= before_tenant_device_count
    assert body["devices"]["total"] <= before_tenant_device_count + 1
    assert body["alerts"]["total"] == before_tenant_alert_count + 1


def test_observability_summary_global_admin_aggregates_all_tenants(monkeypatch) -> None:
    _ensure_user("obs-global-admin", "AdminPass1!", role="admin", organization_id=None)
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    db = SessionLocal()
    try:
        svc = DeviceService(db)
        svc.register("obs-agg-1-11", "Agg Device 1", None, "1.0.0", organization_id=11)
        svc.register("obs-agg-2-12", "Agg Device 2", None, "1.0.0", organization_id=12)
        db.add(Alert(organization_id=11, level="warning", source="system", message="agg1", status="open"))
        db.add(Alert(organization_id=12, level="warning", source="system", message="agg2", status="resolved"))
        db.commit()
    finally:
        db.close()

    token = create_access_token(subject="obs-global-admin", role="admin")
    response = client.get(
        "/api/v1/observability/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["devices"]["total"] >= 2
    assert body["alerts"]["total"] >= 2


def test_observability_summary_rejects_unscoped_non_admin(monkeypatch) -> None:
    _ensure_user("obs-viewer", "ViewerPass1!", role="operator", organization_id=None)
    monkeypatch.setattr(celery_module.celery_app.control, "inspect", lambda timeout=1.0: _InspectOK())

    token = create_access_token(subject="obs-viewer", role="operator")
    response = client.get(
        "/api/v1/observability/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Organization context required"
