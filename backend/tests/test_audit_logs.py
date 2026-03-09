from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.repositories.security_repository import SecurityRepository
from backend.app.services.settings_service import SettingsService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_settings_changes_create_audit_logs_and_filtering() -> None:
    db = _db_session()
    svc = SettingsService(db)
    repo = SecurityRepository(db)

    svc.set_many(
        {"site_name": "A", "timezone": "UTC"},
        organization_id=10,
        changed_by="alice",
        actor_role="admin",
    )

    logs = repo.list_audit_logs(organization_id=10)
    assert len(logs) == 2

    filtered = repo.list_audit_logs(organization_id=10, resource_type="setting")
    assert len(filtered) == 2

    by_action = repo.list_audit_logs(organization_id=10, action="settings.change")
    assert len(by_action) == 2

    by_actor = repo.list_audit_logs(organization_id=10, actor_id="alice")
    assert len(by_actor) == 2
