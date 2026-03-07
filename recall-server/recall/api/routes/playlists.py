from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from recall.core.auth import require_role
from recall.db.database import get_db
from recall.services.playlist_service import PlaylistService

router = APIRouter(prefix="/playlists", tags=["playlists"])


class PlaylistCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PlaylistItemPayload(BaseModel):
    media_id: int
    position: int | None = None
    duration_seconds: int | None = None


class SchedulePayload(BaseModel):
    target: str = Field(default="all", min_length=1, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class LayoutPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    definition_json: str = Field(min_length=2, max_length=16384)


@router.post("", dependencies=[Depends(require_role("admin", "operator"))])
def create_playlist(payload: PlaylistCreatePayload, db: Session = Depends(get_db)):
    playlist = PlaylistService(db).create_playlist(payload.name)
    return {"id": playlist.id, "name": playlist.name}


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def list_playlists(db: Session = Depends(get_db)):
    playlists = PlaylistService(db).list_playlists()
    return [{"id": p.id, "name": p.name} for p in playlists]


@router.post(
    "/{playlist_id}/items", dependencies=[Depends(require_role("admin", "operator"))]
)
def add_item(
    playlist_id: int, payload: PlaylistItemPayload, db: Session = Depends(get_db)
):
    svc = PlaylistService(db)
    item = svc.add_item(
        playlist_id,
        payload.media_id,
        payload.position,
        payload.duration_seconds,
    )
    return {
        "id": item.id,
        "playlist_id": item.playlist_id,
        "media_id": item.media_id,
        "position": item.position,
        "duration_seconds": item.duration_seconds,
    }


@router.get(
    "/{playlist_id}/items",
    dependencies=[Depends(require_role("admin", "operator", "viewer"))],
)
def get_items(playlist_id: int, db: Session = Depends(get_db)):
    items = PlaylistService(db).get_items(playlist_id)
    return [
        {
            "id": i.id,
            "playlist_id": i.playlist_id,
            "media_id": i.media_id,
            "position": i.position,
            "duration_seconds": i.duration_seconds,
        }
        for i in items
    ]


@router.post(
    "/{playlist_id}/schedule",
    dependencies=[Depends(require_role("admin", "operator"))],
)
def schedule_playlist(
    playlist_id: int,
    payload: SchedulePayload,
    db: Session = Depends(get_db),
):
    if payload.ends_at and payload.starts_at and payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    schedule = PlaylistService(db).schedule_playlist(
        playlist_id=playlist_id,
        target=payload.target,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    return {
        "id": schedule.id,
        "playlist_id": schedule.playlist_id,
        "target": schedule.target,
        "starts_at": schedule.starts_at,
        "ends_at": schedule.ends_at,
    }


@router.post("/layouts", dependencies=[Depends(require_role("admin", "operator"))])
def create_layout(payload: LayoutPayload, db: Session = Depends(get_db)):
    layout = PlaylistService(db).create_layout(payload.name, payload.definition_json)
    return {
        "id": layout.id,
        "name": layout.name,
        "definition_json": layout.definition_json,
    }


@router.get(
    "/layouts", dependencies=[Depends(require_role("admin", "operator", "viewer"))]
)
def list_layouts(db: Session = Depends(get_db)):
    return [
        {
            "id": layout.id,
            "name": layout.name,
            "definition_json": layout.definition_json,
        }
        for layout in PlaylistService(db).list_layouts()
    ]
