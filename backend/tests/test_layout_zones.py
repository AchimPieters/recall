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
    layout = svc.create_layout("L1", '{"w":1920,"h":1080}')
    zone = svc.add_zone(layout_id=layout.id, name="main", x=0, y=0, width=960, height=1080)
    svc.assign_zone_playlist(zone_id=zone.id, playlist_id=p.id)

    preview = svc.get_layout_preview(layout.id)
    assert preview["layout"]["id"] == layout.id
    assert len(preview["zones"]) == 1
    assert preview["zones"][0]["playlist_id"] == p.id
