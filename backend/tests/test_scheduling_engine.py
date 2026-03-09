from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.playlist_service import PlaylistService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_schedule_priority_resolution() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    low = svc.create_playlist("Low")
    high = svc.create_playlist("High")
    svc.add_item(low.id, media_id=1, content_type="image")
    svc.add_item(high.id, media_id=2, content_type="image")

    now = datetime.now(timezone.utc)

    svc.schedule_playlist(low.id, target="dev-x", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=5), priority=10)
    svc.schedule_playlist(high.id, target="dev-x", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=5), priority=500)

    resolved = svc.resolve_active_playlist_id_at("dev-x", now)
    assert resolved == high.id


def test_schedule_preview_returns_none_outside_window() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("Timed")
    svc.add_item(p.id, media_id=3, content_type="image")
    now = datetime.now(timezone.utc)
    svc.schedule_playlist(
        p.id,
        target="dev-y",
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(minutes=60),
        priority=100,
    )

    assert svc.resolve_active_playlist_id_at("dev-y", now) is None


def test_schedule_exception_blocks_resolution() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("With exception")
    svc.add_item(p.id, media_id=4, content_type="image")
    now = datetime.now(timezone.utc)
    sched = svc.schedule_playlist(
        p.id,
        target="dev-z",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        priority=100,
    )
    svc.add_schedule_exception(
        schedule_id=sched.id,
        starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(minutes=5),
        reason="maintenance",
    )

    assert svc.resolve_active_playlist_id_at("dev-z", now) is None


def test_blackout_window_blocks_resolution() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("With blackout")
    svc.add_item(p.id, media_id=5, content_type="image")
    now = datetime.now(timezone.utc)
    svc.schedule_playlist(
        p.id,
        target="dev-b",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        priority=100,
    )
    svc.add_blackout_window(
        target="dev-b",
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(minutes=1),
        reason="blackout",
    )

    assert svc.resolve_active_playlist_id_at("dev-b", now) is None
