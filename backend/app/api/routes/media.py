from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_permission
from backend.app.core.config import get_settings
from backend.app.core.security import clamav_scan
from backend.app.db.database import get_db
from backend.app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])
settings = get_settings()


@router.post("/upload", dependencies=[Depends(require_permission("media:write"))])
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
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

    media = service.store_upload(
        file.filename or "upload.bin", mime, data, user.organization_id
    )
    return {
        "id": media.id,
        "name": media.name,
        "path": media.path,
        "thumbnail": media.thumbnail_path,
    }


@router.get("", dependencies=[Depends(require_permission("media:read"))])
def list_media(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    return [
        {
            "id": m.id,
            "organization_id": m.organization_id,
            "name": m.name,
            "path": m.path,
            "mime_type": m.mime_type,
            "thumbnail": m.thumbnail_path,
            "uploaded_at": m.uploaded_at,
        }
        for m in MediaService(db).list_media(user.organization_id)
    ]
