from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.playlist_service import PlaylistService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_layout_zone_playlist_preview() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("Zone Playlist")
    svc.add_item(p.id, media_id=1, content_type="image")
    layout = svc.create_layout("L1", '{"w":1920,"h":1080}')
    zone = svc.add_zone(
        layout_id=layout.id, name="main", x=0, y=0, width=960, height=1080
    )
    svc.assign_zone_playlist(zone_id=zone.id, playlist_id=p.id)

    preview = svc.get_layout_preview(layout.id)
    assert preview["layout"]["id"] == layout.id
    assert len(preview["zones"]) == 1
    assert preview["zones"][0]["playlist_id"] == p.id


def test_resolve_zone_playback_plan_for_device() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    p = svc.create_playlist("Zone Playlist")
    svc.add_item(p.id, media_id=2, content_type="image")
    layout = svc.create_layout("L1", '{"w":1920,"h":1080}')
    zone = svc.add_zone(
        layout_id=layout.id, name="right", x=960, y=0, width=960, height=1080
    )
    svc.assign_zone_playlist(zone_id=zone.id, playlist_id=p.id)

    plan = svc.resolve_zone_playback_plan("dev-any")
    assert len(plan) == 1
    assert plan[0]["zone_name"] == "right"
    assert plan[0]["playlist_id"] == p.id


def test_resolve_zone_playback_uses_latest_layout_and_device_fallback() -> None:
    db = _db_session()
    svc = PlaylistService(db)

    # fallback playlist via device assignment
    fallback = svc.create_playlist("Fallback")
    svc.add_item(fallback.id, media_id=3, content_type="image")
    svc.add_assignment(playlist_id=fallback.id, target_type="device", target_id="dev-1")

    older = svc.create_layout("Old", '{"w":1920,"h":1080}')
    old_zone = svc.add_zone(
        layout_id=older.id, name="old-zone", x=0, y=0, width=500, height=500
    )
    svc.assign_zone_playlist(zone_id=old_zone.id, playlist_id=fallback.id)

    latest = svc.create_layout("Latest", '{"w":1920,"h":1080}')
    svc.add_zone(
        layout_id=latest.id, name="latest-zone", x=100, y=100, width=800, height=800
    )

    plan = svc.resolve_zone_playback_plan("dev-1")

    assert len(plan) == 1
    assert plan[0]["layout_id"] == latest.id
    assert plan[0]["zone_name"] == "latest-zone"
    # no zone assignment -> device fallback playlist should be used
    assert plan[0]["playlist_id"] == fallback.id
