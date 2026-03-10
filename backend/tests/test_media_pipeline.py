from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models.media import MediaVersion
from backend.app.services import media_service as media_service_module
from backend.app.services.media_service import LocalStorageBackend, MediaService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _png_bytes(color: str, size: tuple[int, int] = (16, 16)) -> bytes:
    img = Image.new("RGB", size, color=color)
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

    versions = (
        db.query(MediaVersion)
        .filter(MediaVersion.media_id == first.id)
        .order_by(MediaVersion.version)
        .all()
    )
    assert [v.version for v in versions] == [1, 2]


def test_image_metadata_is_stored(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))

    svc = MediaService(db)
    media = svc.store_upload("poster.png", "image/png", _png_bytes("green", (20, 30)), organization_id=1)
    latest = svc.latest_version(media.id)

    assert latest is not None
    assert latest.width == 20
    assert latest.height == 30
    assert latest.codec == "png"
    assert latest.file_size is not None and latest.file_size > 0
    assert latest.checksum is not None


def test_corrupt_image_rejected(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))

    svc = MediaService(db)
    with pytest.raises(ValueError, match="Corrupt image upload"):
        svc.store_upload("broken.png", "image/png", b"not-a-real-image", organization_id=1)


def test_local_storage_backend_blocks_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorageBackend(tmp_path)
    with pytest.raises(ValueError, match="Invalid storage path"):
        storage.write_bytes("../escape.bin", b"x")


def test_local_storage_backend_allows_nested_relative_paths(tmp_path: Path) -> None:
    storage = LocalStorageBackend(tmp_path)
    target = storage.write_bytes("nested/file.bin", b"abc")
    assert target.exists()
    assert target.read_bytes() == b"abc"
