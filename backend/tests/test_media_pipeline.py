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


def test_validate_upload_rejects_mime_extension_mismatch(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))
    svc = MediaService(db)

    with pytest.raises(ValueError, match="File extension does not match MIME type"):
        svc.validate_upload("file.mp4", 20, "image/png", b"x" * 20)


def test_validate_upload_rejects_invalid_video_container(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))
    svc = MediaService(db)

    with pytest.raises(ValueError, match="Invalid MP4 container"):
        svc.validate_upload("clip.mp4", 64, "video/mp4", b"not-an-mp4-container")


def test_media_workflow_default_and_valid_transitions(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))
    svc = MediaService(db)

    media = svc.store_upload("poster.png", "image/png", _png_bytes("green"), organization_id=1)
    assert media.workflow_state == "draft"

    review = svc.transition_workflow_state(media.id, "review", organization_id=1)
    assert review.workflow_state == "review"

    approved = svc.transition_workflow_state(media.id, "approved", organization_id=1)
    assert approved.workflow_state == "approved"


def test_media_workflow_rejects_invalid_or_forbidden_transitions(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))
    svc = MediaService(db)
    media = svc.store_upload("poster.png", "image/png", _png_bytes("green"), organization_id=1)

    with pytest.raises(ValueError, match="unsupported workflow state"):
        svc.transition_workflow_state(media.id, "not-a-real-state", organization_id=1)

    with pytest.raises(ValueError, match="invalid workflow transition"):
        svc.transition_workflow_state(media.id, "published", organization_id=1)


def test_media_workflow_transition_enforces_organization_scope(tmp_path: Path, monkeypatch) -> None:
    db = _db_session()
    monkeypatch.setattr(media_service_module.settings, "media_dir", str(tmp_path))
    svc = MediaService(db)
    media = svc.store_upload("poster.png", "image/png", _png_bytes("green"), organization_id=1)

    with pytest.raises(ValueError, match="media not found"):
        svc.transition_workflow_state(media.id, "review", organization_id=999)
