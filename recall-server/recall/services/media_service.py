import mimetypes
import subprocess  # nosec B404
from pathlib import Path
from uuid import uuid4
from PIL import Image
from sqlalchemy.orm import Session
from recall.core.config import get_settings
from recall.models.media import Media

settings = get_settings()
ALLOWED_MIME_PREFIXES = ("image/", "video/")


class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.media_dir = Path(settings.media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def validate_upload(self, filename: str, size: int, mime_type: str) -> None:
        if size > settings.max_upload_bytes:
            raise ValueError("Upload too large")
        if not any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
            raise ValueError("Unsupported MIME type")
        if Path(filename).name in {"", ".", ".."}:
            raise ValueError("Invalid filename")

    def store_upload(self, original_name: str, mime_type: str, data: bytes) -> Media:
        ext = (
            Path(original_name).suffix or mimetypes.guess_extension(mime_type) or ".bin"
        )
        filename = f"{uuid4().hex}{ext}"
        path = self.media_dir / filename
        path.write_bytes(data)
        thumb = self._thumbnail(path, mime_type)
        duration = self._duration(path, mime_type)
        media = Media(
            name=original_name,
            path=str(path),
            mime_type=mime_type,
            thumbnail_path=thumb,
            duration_seconds=duration,
        )
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media

    def _thumbnail(self, path: Path, mime_type: str) -> str | None:
        if not mime_type.startswith("image/"):
            return None
        thumb_path = path.with_suffix(".thumb.jpg")
        with Image.open(path) as img:
            img.thumbnail((320, 320))
            img.convert("RGB").save(thumb_path, "JPEG")
        return str(thumb_path)

    def _duration(self, path: Path, mime_type: str) -> int | None:
        if not mime_type.startswith("video/"):
            return None
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
        if proc.returncode != 0:
            return None
        try:
            return int(float(proc.stdout.strip()))
        except ValueError:
            return None
