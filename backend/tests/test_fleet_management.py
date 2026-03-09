from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.device_service import DeviceService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_device_tags_and_filters() -> None:
    db = _db_session()
    svc = DeviceService(db)

    svc.register("d1", "Device 1", None, "1.0.0", organization_id=1)
    svc.register("d2", "Device 2", None, "1.0.1", organization_id=1)
    svc.assign_tag("d1", "lobby", organization_id=1)

    tagged = svc.list_devices(organization_id=1, tag="lobby")
    assert [d.id for d in tagged] == ["d1"]

    by_version = svc.list_devices(organization_id=1, version="1.0.1")
    assert [d.id for d in by_version] == ["d2"]


def test_device_group_filter_and_last_seen_filter() -> None:
    db = _db_session()
    svc = DeviceService(db)

    d1 = svc.register("g1", "Group Device", None, "1.0.0", organization_id=1)
    d2 = svc.register("g2", "Other Device", None, "1.0.0", organization_id=1)

    group = svc.create_group("Store-1", organization_id=1)
    svc.assign_group_member(group.id, d1.id)

    in_group = svc.list_devices(organization_id=1, group_id=group.id)
    assert [d.id for d in in_group] == ["g1"]

    d2.last_seen = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db.commit()

    stale = svc.list_devices(
        organization_id=1,
        last_seen_before=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )
    assert [d.id for d in stale] == ["g2"]
