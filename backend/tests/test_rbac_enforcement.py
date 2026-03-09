import pytest

from backend.app.core.auth import role_has_permission
from backend.app.db.database import Base
from backend.app.services.settings_service import SettingsService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_permission_alias_support_dot_and_colon() -> None:
    assert role_has_permission("admin", "settings.write")
    assert role_has_permission("admin", "devices.manage")
    assert role_has_permission("viewer", "settings.read")
    assert not role_has_permission("viewer", "settings.write")


def test_service_permission_enforced_for_settings_write() -> None:
    db = _db_session()
    service = SettingsService(db)

    with pytest.raises(PermissionError):
        service.set_many(
            {"site_name": "Denied"},
            changed_by="viewer-user",
            actor_role="viewer",
        )

    data = service.set_many(
        {"site_name": "Allowed"},
        changed_by="admin-user",
        actor_role="admin",
    )
    assert data["site_name"] == "Allowed"
