from datetime import datetime, timedelta, timezone

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
        scope="organization",
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


def test_audit_log_extended_filters() -> None:
    db = _db_session()
    repo = SecurityRepository(db)

    row1 = repo.add_audit_log(
        actor_type="user",
        actor_id="alice",
        organization_id=42,
        action="settings.change",
        resource_type="setting",
        resource_id="organization:-:site_name",
        before_state="A",
        after_state="B",
        ip_address="10.0.0.1",
        user_agent="pytest",
    )
    repo.add_audit_log(
        actor_type="user",
        actor_id="bob",
        organization_id=42,
        action="settings.rollback",
        resource_type="setting",
        resource_id="organization:-:timezone",
        before_state="UTC",
        after_state="CET",
        ip_address="10.0.0.2",
        user_agent="pytest",
    )

    assert len(repo.list_audit_logs(organization_id=42, actor_type="user")) == 2
    assert len(repo.list_audit_logs(organization_id=42, ip_address="10.0.0.1")) == 1
    assert (
        len(
            repo.list_audit_logs(
                organization_id=42,
                resource_id="organization:-:site_name",
            )
        )
        == 1
    )

    created_from = row1.created_at - timedelta(seconds=1)
    created_to = datetime.now(timezone.utc) + timedelta(seconds=1)
    assert (
        len(
            repo.list_audit_logs(
                organization_id=42,
                created_from=created_from,
                created_to=created_to,
            )
        )
        == 2
    )
