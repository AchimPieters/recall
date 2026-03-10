import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.settings_service import SettingsService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_settings_scopes_are_isolated() -> None:
    db = _db_session()
    svc = SettingsService(db)

    svc.set_many({"site_name": "Global"}, scope="global", changed_by="admin")
    svc.set_many(
        {"site_name": "Org10"},
        scope="organization",
        organization_id=10,
        changed_by="admin",
    )
    svc.set_many(
        {"site_name": "DeviceA"},
        scope="device",
        organization_id=10,
        device_id="dev-a",
        changed_by="admin",
    )

    assert svc.get_all(scope="global")["site_name"] == "Global"
    assert svc.get_all(scope="organization", organization_id=10)["site_name"] == "Org10"
    assert (
        svc.get_all(scope="device", organization_id=10, device_id="dev-a")["site_name"]
        == "DeviceA"
    )


def test_device_scope_requires_target() -> None:
    db = _db_session()
    svc = SettingsService(db)

    with pytest.raises(ValueError):
        svc.set_many(
            {"site_name": "Bad"},
            scope="device",
            organization_id=10,
            changed_by="admin",
        )


def test_global_scope_rejects_org_or_device_target() -> None:
    db = _db_session()
    svc = SettingsService(db)

    with pytest.raises(ValueError, match="Global settings cannot target"):
        svc.set_many(
            {"site_name": "BadGlobal"},
            scope="global",
            organization_id=10,
            changed_by="admin",
        )

    with pytest.raises(ValueError, match="Global settings cannot target"):
        svc.set_many(
            {"site_name": "BadGlobal"},
            scope="global",
            device_id="dev-x",
            changed_by="admin",
        )


def test_organization_scope_rejects_device_target() -> None:
    db = _db_session()
    svc = SettingsService(db)

    with pytest.raises(ValueError, match="cannot target device_id"):
        svc.set_many(
            {"site_name": "OrgBad"},
            scope="organization",
            organization_id=10,
            device_id="dev-x",
            changed_by="admin",
        )


def test_invalid_scope_is_rejected() -> None:
    db = _db_session()
    svc = SettingsService(db)

    with pytest.raises(ValueError, match="Unsupported settings scope"):
        svc.set_many(
            {"site_name": "BadScope"},
            scope="tenant",
            changed_by="admin",
        )
