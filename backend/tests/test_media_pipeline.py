from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models.media import MediaVersion
from backend.app.services import media_service as media_service_module
from backend.app.services.media_service import MediaService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _png_bytes(color: str) -> bytes:
    img = Image.new("RGB", (16, 16), color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_media_duplicate_detection_and_versioning(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))

    svc = MediaService(db)
    first = svc.store_upload("banner.png", "image/png", _png_bytes("red"), organization_id=1)
    same = svc.store_upload("copy.png", "image/png", _png_bytes("red"), organization_id=1)
    assert same.id == first.id

    updated = svc.store_upload("banner.png", "image/png", _png_bytes("blue"), organization_id=1)
    assert updated.id == first.id

    versions = db.query(MediaVersion).filter(MediaVersion.media_id == first.id).order_by(MediaVersion.version).all()
    assert [v.version for v in versions] == [1, 2]
