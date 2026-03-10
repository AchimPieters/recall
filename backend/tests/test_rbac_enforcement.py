from fastapi import HTTPException
import pytest

from backend.app.core.auth import AuthUser, ensure_organization_access, oauth2_scheme, role_has_permission
from backend.app.db.database import Base
from backend.app.services.device_service import DeviceService
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
    assert role_has_permission("admin", "media:write")
    assert role_has_permission("viewer", "settings.read")
    assert not role_has_permission("viewer", "settings.write")


def test_superadmin_has_user_write_permission() -> None:
    assert role_has_permission("superadmin", "users.write")


def test_service_permission_enforced_for_settings_write() -> None:
    db = _db_session()
    service = SettingsService(db)

    with pytest.raises(PermissionError):
        service.set_many(
            {"site_name": "Denied"},
            scope="global",
            changed_by="viewer-user",
            actor_role="viewer",
        )

    data = service.set_many(
        {"site_name": "Allowed"},
        scope="global",
        changed_by="admin-user",
        actor_role="admin",
    )
    assert data["site_name"] == "Allowed"


def test_device_service_enforces_manage_permission_for_bulk_actions() -> None:
    db = _db_session()
    svc = DeviceService(db)

    with pytest.raises(PermissionError):
        svc.execute_group_action(
            group_id=1,
            action="reboot",
            actor="viewer-user",
            organization_id=None,
            actor_role="viewer",
        )


def test_oauth2_password_flow_uses_versioned_token_url() -> None:
    assert oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/token"


def test_ensure_organization_access_requires_context_for_non_admin_without_org() -> None:
    user = AuthUser(username="u1", role="viewer", organization_id=None)
    with pytest.raises(HTTPException, match="Organization context required"):
        ensure_organization_access(user, organization_id=10)


def test_ensure_organization_access_blocks_cross_org_for_scoped_user() -> None:
    user = AuthUser(username="u2", role="operator", organization_id=5)
    with pytest.raises(HTTPException, match="Cross-organization access denied"):
        ensure_organization_access(user, organization_id=6)


def test_ensure_organization_access_allows_platform_admin_without_org_scope() -> None:
    user = AuthUser(username="sa", role="superadmin", organization_id=None)
    ensure_organization_access(user, organization_id=999)
