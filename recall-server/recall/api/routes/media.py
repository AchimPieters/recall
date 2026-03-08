from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from recall.core.auth import require_permission
from recall.core.config import get_settings
from recall.core.security import clamav_scan
from recall.db.database import get_db
from recall.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])
settings = get_settings()


@router.post("/upload", dependencies=[Depends(require_permission("media:write"))])
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    service = MediaService(db)
    try:
        service.validate_upload(file.filename or "upload.bin", len(data), mime)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not clamav_scan(
        data,
        host=settings.clamav_host,
        port=settings.clamav_port,
        fail_open=settings.clamav_fail_open,
    ):
        raise HTTPException(400, "Malware detected")

    media = service.store_upload(file.filename or "upload.bin", mime, data)
    return {
        "id": media.id,
        "name": media.name,
        "path": media.path,
        "thumbnail": media.thumbnail_path,
    }
