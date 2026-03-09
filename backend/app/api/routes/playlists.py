from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import require_permission
from backend.app.db.database import get_db
from backend.app.services.playlist_service import PlaylistService

router = APIRouter(prefix="/playlists", tags=["playlists"])


class PlaylistCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PlaylistItemPayload(BaseModel):
    media_id: int
    position: int | None = None
    duration_seconds: int | None = None


class PlaylistAssignmentPayload(BaseModel):
    target_type: str = Field(pattern="^(device|group)$")
    target_id: str = Field(min_length=1, max_length=64)
    is_fallback: bool = False
    priority: int = Field(default=100, ge=1, le=10000)


class PlaylistRulePayload(BaseModel):
    rule_type: str = Field(min_length=1, max_length=64)
    rule_value: str = Field(min_length=1, max_length=1024)


class SchedulePayload(BaseModel):
    target: str = Field(default="all", min_length=1, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence: str | None = Field(default=None, max_length=128)
    priority: int = Field(default=100, ge=1, le=10000)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)


class LayoutPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    definition_json: str = Field(min_length=2, max_length=16384)


class ZonePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080


class ZonePlaylistPayload(BaseModel):
    playlist_id: int = Field(ge=1)


@router.post("", dependencies=[Depends(require_permission("playlists:write"))])
def create_playlist(payload: PlaylistCreatePayload, db: Session = Depends(get_db)):
    playlist = PlaylistService(db).create_playlist(payload.name)
    return {"id": playlist.id, "name": playlist.name}


@router.get("", dependencies=[Depends(require_permission("playlists:read"))])
def list_playlists(db: Session = Depends(get_db)):
    playlists = PlaylistService(db).list_playlists()
    return [{"id": p.id, "name": p.name} for p in playlists]


@router.post(
    "/{playlist_id}/items",
    dependencies=[Depends(require_permission("playlists:write"))],
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


@router.post(
    "/{playlist_id}/assign",
    dependencies=[Depends(require_permission("playlists:write"))],
)
def assign_playlist(
    playlist_id: int,
    payload: PlaylistAssignmentPayload,
    db: Session = Depends(get_db),
):
    assignment = PlaylistService(db).add_assignment(
        playlist_id=playlist_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        is_fallback=payload.is_fallback,
        priority=payload.priority,
    )
    return {
        "id": assignment.id,
        "playlist_id": assignment.playlist_id,
        "target_type": assignment.target_type,
        "target_id": assignment.target_id,
        "is_fallback": bool(assignment.is_fallback),
        "priority": assignment.priority,
    }


@router.post(
    "/{playlist_id}/rules",
    dependencies=[Depends(require_permission("playlists:write"))],
)
def add_rule(playlist_id: int, payload: PlaylistRulePayload, db: Session = Depends(get_db)):
    rule = PlaylistService(db).add_rule(
        playlist_id=playlist_id, rule_type=payload.rule_type, rule_value=payload.rule_value
    )
    return {
        "id": rule.id,
        "playlist_id": rule.playlist_id,
        "rule_type": rule.rule_type,
        "rule_value": rule.rule_value,
    }


@router.get(
    "/{playlist_id}/items",
    dependencies=[Depends(require_permission("playlists:read"))],
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
    dependencies=[Depends(require_permission("playlists:write"))],
)
def schedule_playlist(
    playlist_id: int,
    payload: SchedulePayload,
    db: Session = Depends(get_db),
):
    try:
        schedule = PlaylistService(db).schedule_playlist(
            playlist_id=playlist_id,
            target=payload.target,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            recurrence=payload.recurrence,
            priority=payload.priority,
            timezone_name=payload.timezone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": schedule.id,
        "playlist_id": schedule.playlist_id,
        "target": schedule.target,
        "starts_at": schedule.starts_at,
        "ends_at": schedule.ends_at,
        "recurrence": schedule.recurrence,
        "priority": schedule.priority,
        "timezone": schedule.timezone,
    }




@router.get("/resolve/preview", dependencies=[Depends(require_permission("playlists:read"))])
def preview_resolution(target: str, at: datetime | None = None, db: Session = Depends(get_db)):
    playlist_id = PlaylistService(db).resolve_active_playlist_id_at(target, at)
    return {"target": target, "at": at, "playlist_id": playlist_id}


@router.get("/resolve/device/{device_id}", dependencies=[Depends(require_permission("playlists:read"))])
def resolve_for_device(device_id: str, db: Session = Depends(get_db)):
    return PlaylistService(db).resolve_for_device(device_id)


@router.post("/layouts", dependencies=[Depends(require_permission("playlists:write"))])
def create_layout(payload: LayoutPayload, db: Session = Depends(get_db)):
    layout = PlaylistService(db).create_layout(payload.name, payload.definition_json)
    return {
        "id": layout.id,
        "name": layout.name,
        "definition_json": layout.definition_json,
    }




@router.post("/layouts/{layout_id}/zones", dependencies=[Depends(require_permission("playlists:write"))])
def add_zone(layout_id: int, payload: ZonePayload, db: Session = Depends(get_db)):
    zone = PlaylistService(db).add_zone(
        layout_id=layout_id,
        name=payload.name,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
    )
    return {
        "id": zone.id,
        "layout_id": zone.layout_id,
        "name": zone.name,
        "x": zone.x,
        "y": zone.y,
        "width": zone.width,
        "height": zone.height,
    }


@router.post("/zones/{zone_id}/playlist", dependencies=[Depends(require_permission("playlists:write"))])
def assign_zone_playlist(zone_id: int, payload: ZonePlaylistPayload, db: Session = Depends(get_db)):
    assignment = PlaylistService(db).assign_zone_playlist(zone_id=zone_id, playlist_id=payload.playlist_id)
    return {"id": assignment.id, "zone_id": assignment.zone_id, "playlist_id": assignment.playlist_id}


@router.get("/layouts/{layout_id}/preview", dependencies=[Depends(require_permission("playlists:read"))])
def layout_preview(layout_id: int, db: Session = Depends(get_db)):
    preview = PlaylistService(db).get_layout_preview(layout_id)
    if preview["layout"] is None:
        raise HTTPException(status_code=404, detail="layout not found")
    return preview


@router.get("/layouts", dependencies=[Depends(require_permission("playlists:read"))])
def list_layouts(db: Session = Depends(get_db)):
    return [
        {
            "id": layout.id,
            "name": layout.name,
            "definition_json": layout.definition_json,
        }
        for layout in PlaylistService(db).list_layouts()
    ]
