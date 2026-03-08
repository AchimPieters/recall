from pathlib import Path

from recall.db.database import Base, SessionLocal, engine
from recall.services.media_service import MediaService


def test_video_duration_returns_none_when_ffprobe_missing(
    monkeypatch, tmp_path: Path
) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        svc = MediaService(db)
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"not-a-real-video")

        def _raise(*args, **kwargs):
            raise FileNotFoundError("ffprobe not found")

        monkeypatch.setattr("recall.services.media_service.subprocess.run", _raise)
        assert svc._duration(video_path, "video/mp4") is None
    finally:
        db.close()


def test_video_duration_returns_none_on_probe_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        svc = MediaService(db)
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"not-a-real-video")

        import subprocess

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=1)

        monkeypatch.setattr("recall.services.media_service.subprocess.run", _timeout)
        assert svc._duration(video_path, "video/mp4") is None
    finally:
        db.close()
