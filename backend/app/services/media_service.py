import json
import hashlib
import mimetypes
import subprocess  # nosec B404
from io import BytesIO
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.events import MEDIA_UPLOADED, make_event, publisher
from backend.app.core.config import get_settings
from backend.app.models.event import Event
from backend.app.models.media import Media, MediaVersion

settings = get_settings()
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "video/mp4",
    "video/webm",
}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm"}
MIME_EXTENSION_MAP = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "video/mp4": {".mp4"},
    "video/webm": {".webm"},
}


WORKFLOW_STATES = {"draft", "review", "approved", "published", "archived"}
WORKFLOW_TRANSITIONS = {
    "draft": {"review", "archived"},
    "review": {"approved", "draft", "archived"},
    "approved": {"published", "review", "archived"},
    "published": {"archived"},
    "archived": set(),
}


class StorageBackend(Protocol):
    def write_bytes(self, relative_name: str, data: bytes) -> Path: ...


class LocalStorageBackend:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, relative_name: str, data: bytes) -> Path:
        target = (self.base_dir / relative_name).resolve()
        base = self.base_dir.resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise ValueError("Invalid storage path") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target


class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.media_dir = Path(settings.media_dir)
        self.storage: StorageBackend = LocalStorageBackend(self.media_dir)

    def validate_upload(
        self, filename: str, size: int, mime_type: str, data: bytes | None = None
    ) -> None:
        if size > settings.max_upload_bytes:
            raise ValueError("Upload too large")
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError("Unsupported MIME type")
        clean_name = Path(filename).name
        if clean_name in {"", ".", ".."}:
            raise ValueError("Invalid filename")
        ext = Path(clean_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("Blocked file extension")
        if ext not in MIME_EXTENSION_MAP.get(mime_type, set()):
            raise ValueError("File extension does not match MIME type")
        if data is not None:
            self._validate_file_structure(mime_type, data)

    def _validate_file_structure(self, mime_type: str, data: bytes) -> None:
        if mime_type.startswith("image/"):
            try:
                with Image.open(BytesIO(data)) as img:
                    img.verify()
            except (UnidentifiedImageError, OSError) as exc:
                raise ValueError("Invalid image structure") from exc
            return

        head = data[:16]
        if mime_type == "video/mp4":
            if b"ftyp" not in head and b"ftyp" not in data[:128]:
                raise ValueError("Invalid MP4 container")
            return
        if mime_type == "video/webm":
            if not data.startswith(b"\x1aE\xdf\xa3"):
                raise ValueError("Invalid WebM container")
            return

    def _checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _find_duplicate(
        self, checksum: str, organization_id: int | None
    ) -> Media | None:
        query = self.db.query(Media).join(
            MediaVersion, MediaVersion.media_id == Media.id
        )
        if organization_id is not None:
            query = query.filter(Media.organization_id == organization_id)
        else:
            query = query.filter(Media.organization_id.is_(None))
        return (
            query.filter(MediaVersion.checksum == checksum)
            .order_by(Media.id.desc())
            .first()
        )

    def _next_version(self, media_id: int) -> int:
        current = (
            self.db.query(func.max(MediaVersion.version))
            .filter(MediaVersion.media_id == media_id)
            .scalar()
        )
        return int(current or 0) + 1

    def _inspect_image(self, path: Path) -> dict:
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img2:
                width, height = img2.size
                codec = (img2.format or "").lower() or None
            return {
                "width": width,
                "height": height,
                "codec": codec,
                "duration_seconds": None,
            }
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError(f"Corrupt image upload: {exc}") from exc

    def _inspect_video(self, path: Path) -> dict:
        cmd = [
            settings.ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height:format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=0",
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
            return {
                "width": None,
                "height": None,
                "codec": None,
                "duration_seconds": None,
            }

        if proc.returncode != 0:
            return {
                "width": None,
                "height": None,
                "codec": None,
                "duration_seconds": None,
            }

        parsed: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()

        try:
            duration = (
                int(float(parsed.get("duration", "0")))
                if parsed.get("duration")
                else None
            )
        except ValueError:
            duration = None

        def _to_int(v: str | None) -> int | None:
            if not v:
                return None
            try:
                return int(v)
            except ValueError:
                return None

        return {
            "width": _to_int(parsed.get("width")),
            "height": _to_int(parsed.get("height")),
            "codec": parsed.get("codec_name"),
            "duration_seconds": duration,
        }

    def store_upload(
        self,
        original_name: str,
        mime_type: str,
        data: bytes,
        organization_id: int | None,
    ) -> Media:
        checksum = self._checksum(data)
        duplicate = self._find_duplicate(checksum, organization_id)
        if duplicate:
            return duplicate

        ext = (
            Path(original_name).suffix or mimetypes.guess_extension(mime_type) or ".bin"
        )
        filename = f"{uuid4().hex}{ext}"
        path = self.storage.write_bytes(filename, data)

        if mime_type.startswith("image/"):
            meta = self._inspect_image(path)
        elif mime_type.startswith("video/"):
            meta = self._inspect_video(path)
        else:
            meta = {
                "width": None,
                "height": None,
                "codec": None,
                "duration_seconds": None,
            }

        thumb = self._thumbnail(path, mime_type)

        media = (
            self.db.query(Media)
            .filter(
                Media.organization_id == organization_id, Media.name == original_name
            )
            .first()
        )
        if media:
            media.path = str(path)
            media.mime_type = mime_type
            media.thumbnail_path = thumb
            media.duration_seconds = meta["duration_seconds"]
            version = self._next_version(media.id)
        else:
            media = Media(
                organization_id=organization_id,
                name=original_name,
                path=str(path),
                mime_type=mime_type,
                thumbnail_path=thumb,
                duration_seconds=meta["duration_seconds"],
            )
            self.db.add(media)
            self.db.flush()
            version = 1

        self.db.add(
            MediaVersion(
                media_id=media.id,
                version=version,
                path=str(path),
                checksum=checksum,
                file_size=len(data),
                codec=meta["codec"],
                width=meta["width"],
                height=meta["height"],
                duration_seconds=meta["duration_seconds"],
            )
        )
        self.db.commit()
        self.db.refresh(media)
        publisher.publish(
            make_event(
                MEDIA_UPLOADED,
                {
                    "media_id": media.id,
                    "name": media.name,
                    "organization_id": organization_id,
                },
            )
        )
        return media

    def latest_version(self, media_id: int) -> MediaVersion | None:
        return (
            self.db.query(MediaVersion)
            .filter(MediaVersion.media_id == media_id)
            .order_by(MediaVersion.version.desc())
            .first()
        )

    def list_media(self, organization_id: int | None) -> list[Media]:
        query = self.db.query(Media)
        if organization_id is not None:
            query = query.filter(Media.organization_id == organization_id)
        return (
            query.order_by(Media.uploaded_at.desc(), Media.id.desc()).limit(500).all()
        )

    def transition_workflow_state(
        self,
        media_id: int,
        target_state: str,
        organization_id: int | None = None,
        transition_reason: str | None = None,
    ) -> Media:
        target = (target_state or "").strip().lower()
        if target not in WORKFLOW_STATES:
            raise ValueError("unsupported workflow state")

        query = self.db.query(Media).filter(Media.id == media_id)
        if organization_id is not None:
            query = query.filter(Media.organization_id == organization_id)
        media = query.first()
        if not media:
            raise ValueError("media not found")

        current = (media.workflow_state or "draft").strip().lower()
        if target == current:
            return media
        allowed = WORKFLOW_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"invalid workflow transition {current}->{target}")

        reason = (transition_reason or "").strip() or None
        if target == "draft" and current in {"review", "approved"}:
            if reason is None or len(reason) < 8:
                raise ValueError(
                    "transition reason required when moving back to draft from review/approved"
                )

        media.workflow_state = target
        self.db.add(
            Event(
                organization_id=media.organization_id,
                category="media_workflow",
                action="state_transition",
                actor="media-service",
                payload=json.dumps(
                    {
                        "media_id": media.id,
                        "from_state": current,
                        "to_state": target,
                        "reason": reason,
                    }
                ),
            )
        )
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
