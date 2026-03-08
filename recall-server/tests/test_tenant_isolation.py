from fastapi.testclient import TestClient

from recall.api.main import app
from recall.core.security import create_access_token, get_password_hash
from recall.db.database import Base, SessionLocal, engine
from recall.models.device import Device
from recall.models.settings import Organization, User

client = TestClient(app)


def _upsert_org_and_user(org_id: int, username: str, role: str) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            db.add(Organization(id=org_id, name=f"Org-{org_id}"))
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                password_hash=get_password_hash(username),
                role=role,
                organization_id=org_id,
            )
            db.add(user)
        else:
            user.password_hash = get_password_hash(username)
            user.role = role
            user.organization_id = org_id
        db.commit()
    finally:
        db.close()


def test_device_listing_is_isolated_per_organization() -> None:
    _upsert_org_and_user(101, "org1-operator", "operator")
    _upsert_org_and_user(202, "org2-operator", "operator")

    token_org1 = create_access_token(subject="org1-operator", role="operator")
    token_org2 = create_access_token(subject="org2-operator", role="operator")

    register = client.post(
        "/device/register",
        json={"id": "org1-device", "name": "Org1 Device"},
        headers={"Authorization": f"Bearer {token_org1}"},
    )
    assert register.status_code == 200

    db = SessionLocal()
    try:
        stored = db.query(Device).filter(Device.id == "org1-device").first()
        assert stored is not None
        assert stored.organization_id == 101
    finally:
        db.close()

    org2_devices = client.get(
        "/device/list", headers={"Authorization": f"Bearer {token_org2}"}
    )
    assert org2_devices.status_code == 200
    assert not any(d["id"] == "org1-device" for d in org2_devices.json())
