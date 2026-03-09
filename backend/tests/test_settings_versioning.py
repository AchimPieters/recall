from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models import Setting, SettingVersion, SecurityAuditEvent
from backend.app.services.settings_service import SettingsService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_settings_version_history_and_rollback() -> None:
    db = _db_session()
    service = SettingsService(db)

    service.set_many(
        {"site_name": "Recall A", "timezone": "UTC"},
        organization_id=None,
        changed_by="admin",
        reason="initial",
    )
    service.set_many(
        {"site_name": "Recall B"},
        organization_id=None,
        changed_by="admin",
        reason="update",
    )

    history = service.get_history("site_name")
    assert len(history) == 2
    assert history[0]["version"] == 2
    assert history[0]["setting_value"] == "Recall B"

    rolled = service.rollback(
        key="site_name", target_version=1, organization_id=None, changed_by="admin"
    )
    assert rolled["version"] == 3
    assert rolled["value"] == "Recall A"

    latest = db.query(Setting).filter(Setting.key == "site_name").one()
    assert latest.value == "Recall A"
    assert latest.version == 3

    versions = db.query(SettingVersion).filter(SettingVersion.setting_key == "site_name").all()
    assert len(versions) == 3

    audit = db.query(SecurityAuditEvent).filter(SecurityAuditEvent.event_type == "settings_rollback").all()
    assert len(audit) == 1
