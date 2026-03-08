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
        clean_name = Path(filename).name
        if clean_name in {"", ".", ".."}:
            raise ValueError("Invalid filename")
        ext = Path(clean_name).suffix.lower()
        if ext in {".exe", ".bat", ".cmd", ".sh", ".js", ".jar"}:
            raise ValueError("Blocked file extension")

    def store_upload(
        self,
        original_name: str,
        mime_type: str,
        data: bytes,
        organization_id: int | None,
    ) -> Media:
        ext = (
            Path(original_name).suffix or mimetypes.guess_extension(mime_type) or ".bin"
        )
        filename = f"{uuid4().hex}{ext}"
        path = self.media_dir / filename
        path.write_bytes(data)
        thumb = self._thumbnail(path, mime_type)
        duration = self._duration(path, mime_type)
        media = Media(
            organization_id=organization_id,
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

    def list_media(self, organization_id: int | None) -> list[Media]:
        query = self.db.query(Media)
        if organization_id is not None:
            query = query.filter(Media.organization_id == organization_id)
        return (
            query.order_by(Media.uploaded_at.desc(), Media.id.desc()).limit(500).all()
        )

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
            settings.ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.ffprobe_timeout_seconds,
            )  # nosec B603
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        try:
            return int(float(proc.stdout.strip()))
        except ValueError:
            return None
