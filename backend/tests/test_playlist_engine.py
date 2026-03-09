from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models.device import Device, DeviceGroup, DeviceGroupMember
from backend.app.services.playlist_service import PlaylistService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_playlist_assignments_and_fallback_resolution() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p1 = svc.create_playlist("Primary")
    p2 = svc.create_playlist("Fallback")

    db.add(Device(id="dev-1", name="D1", status="online"))
    db.add(DeviceGroup(id=7, name="Group-7"))
    db.add(DeviceGroupMember(group_id=7, device_id="dev-1"))
    db.commit()

    svc.add_assignment(playlist_id=p2.id, target_type="group", target_id="7", is_fallback=True, priority=200)
    svc.add_assignment(playlist_id=p1.id, target_type="device", target_id="dev-1", is_fallback=False, priority=10)

    resolved = svc.resolve_for_device("dev-1")
    assert resolved["playlist_id"] == p1.id
    assert resolved["source"] == "device_assignment"


def test_schedule_has_precedence_over_assignment() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    sched_playlist = svc.create_playlist("Scheduled")
    assigned_playlist = svc.create_playlist("Assigned")

    db.add(Device(id="dev-2", name="D2", status="online"))
    db.commit()

    svc.add_assignment(playlist_id=assigned_playlist.id, target_type="device", target_id="dev-2")
    svc.schedule_playlist(playlist_id=sched_playlist.id, target="dev-2", starts_at=None, ends_at=None)

    resolved = svc.resolve_for_device("dev-2")
    assert resolved["playlist_id"] == sched_playlist.id
    assert resolved["source"] == "schedule"
