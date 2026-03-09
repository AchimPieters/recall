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
    now = datetime.now(timezone.utc)

    svc.schedule_playlist(low.id, target="dev-x", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=5), priority=10)
    svc.schedule_playlist(high.id, target="dev-x", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=5), priority=500)

    resolved = svc.resolve_active_playlist_id_at("dev-x", now)
    assert resolved == high.id


def test_schedule_preview_returns_none_outside_window() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("Timed")
    now = datetime.now(timezone.utc)
    svc.schedule_playlist(
        p.id,
        target="dev-y",
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(minutes=60),
        priority=100,
    )

    assert svc.resolve_active_playlist_id_at("dev-y", now) is None
