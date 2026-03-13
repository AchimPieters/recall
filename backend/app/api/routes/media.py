from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_permission
from backend.app.core.config import get_settings
from backend.app.core.security import clamav_scan
from backend.app.db.database import get_db
from backend.app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])
settings = get_settings()


class WorkflowTransitionPayload(BaseModel):
    state: str = Field(min_length=3, max_length=32)
    reason: str | None = Field(default=None, max_length=500)


def _enforce_workflow_role(target_state: str, user: AuthUser) -> None:
    target = target_state.strip().lower()
    editor_roles = {"editor", "admin", "superadmin"}
    reviewer_roles = {"reviewer", "admin", "superadmin"}

    if target == "review" and user.role not in editor_roles:
        raise HTTPException(
            status_code=403,
            detail="Only editor/reviewer pipeline roles can move to review",
        )
    if target in {"approved", "published"} and user.role not in reviewer_roles:
        raise HTTPException(
            status_code=403, detail="Only reviewer/admin roles can approve or publish"
        )


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
        service.validate_upload(file.filename or "upload.bin", len(data), mime, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not clamav_scan(
        data,
        host=settings.clamav_host,
        port=settings.clamav_port,
        fail_open=settings.clamav_fail_open,
    ):
        raise HTTPException(400, "Malware detected")

    try:
        media = service.store_upload(
            file.filename or "upload.bin", mime, data, user.organization_id
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    latest = service.latest_version(media.id)
    return {
        "id": media.id,
        "name": media.name,
        "path": media.path,
        "thumbnail": media.thumbnail_path,
        "version": latest.version if latest else None,
        "checksum": latest.checksum if latest else None,
        "file_size": latest.file_size if latest else None,
        "codec": latest.codec if latest else None,
        "width": latest.width if latest else None,
        "height": latest.height if latest else None,
        "duration_seconds": latest.duration_seconds if latest else None,
        "workflow_state": media.workflow_state,
    }


@router.get("", dependencies=[Depends(require_permission("media:read"))])
def list_media(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    service = MediaService(db)
    result = []
    for m in service.list_media(user.organization_id):
        latest = service.latest_version(m.id)
        result.append(
            {
                "id": m.id,
                "organization_id": m.organization_id,
                "name": m.name,
                "path": m.path,
                "mime_type": m.mime_type,
                "thumbnail": m.thumbnail_path,
                "uploaded_at": m.uploaded_at,
                "version": latest.version if latest else None,
                "checksum": latest.checksum if latest else None,
                "file_size": latest.file_size if latest else None,
                "codec": latest.codec if latest else None,
                "width": latest.width if latest else None,
                "height": latest.height if latest else None,
                "duration_seconds": latest.duration_seconds if latest else None,
                "workflow_state": m.workflow_state,
            }
        )
    return result


@router.post(
    "/{media_id}/workflow/transition",
    dependencies=[Depends(require_permission("media:write"))],
)
def transition_media_workflow(
    media_id: int,
    payload: WorkflowTransitionPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    service = MediaService(db)
    _enforce_workflow_role(payload.state, user)
    try:
        media = service.transition_workflow_state(
            media_id,
            payload.state,
            organization_id=user.organization_id,
            transition_reason=payload.reason,
        )
    except ValueError as exc:
        if str(exc) == "media not found":
            raise HTTPException(status_code=404, detail="media not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    latest = service.latest_version(media.id)
    return {
        "id": media.id,
        "workflow_state": media.workflow_state,
        "version": latest.version if latest else None,
    }
