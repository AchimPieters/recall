from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.device import DeviceGroupMember
from backend.app.models.media import (
    Layout,
    Playlist,
    PlaylistAssignment,
    PlaylistItem,
    PlaylistRule,
    Schedule,
    ScheduleBlackoutWindow,
    ScheduleException,
    Zone,
    ZonePlaylistAssignment,
)


class PlaylistService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def create_playlist(self, name: str) -> Playlist:
        playlist = Playlist(name=name)
        self.db.add(playlist)
        self.db.commit()
        self.db.refresh(playlist)
        return playlist

    def list_playlists(self) -> list[Playlist]:
        return self.db.query(Playlist).order_by(Playlist.id.asc()).all()

    def add_item(
        self,
        playlist_id: int,
        media_id: int | None,
        position: int | None = None,
        duration_seconds: int | None = None,
        content_type: str = "image",
        source_url: str | None = None,
        widget_config: str | None = None,
        transition_seconds: int | None = None,
    ) -> PlaylistItem:
        if position is None:
            position = (
                self.db.query(PlaylistItem)
                .filter(PlaylistItem.playlist_id == playlist_id)
                .count()
            )

        allowed_content_types = {"image", "video", "web_url", "widget"}
        if content_type not in allowed_content_types:
            raise ValueError("unsupported content_type")
        if content_type in {"image", "video"} and media_id is None:
            raise ValueError("media_id is required for image/video items")
        if content_type == "web_url" and not source_url:
            raise ValueError("source_url is required for web_url items")
        if content_type == "widget" and not widget_config:
            raise ValueError("widget_config is required for widget items")

        item = PlaylistItem(
            playlist_id=playlist_id,
            media_id=media_id,
            content_type=content_type,
            source_url=source_url,
            widget_config=widget_config,
            position=position,
            duration_seconds=duration_seconds,
            transition_seconds=transition_seconds,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_items(self, playlist_id: int) -> list[PlaylistItem]:
        return (
            self.db.query(PlaylistItem)
            .filter(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc(), PlaylistItem.id.asc())
            .all()
        )

    def add_assignment(
        self,
        *,
        playlist_id: int,
        target_type: str,
        target_id: str,
        is_fallback: bool = False,
        priority: int = 100,
    ) -> PlaylistAssignment:
        if target_type not in {"device", "group"}:
            raise ValueError("target_type must be device or group")
        assignment = PlaylistAssignment(
            playlist_id=playlist_id,
            target_type=target_type,
            target_id=target_id,
            is_fallback=1 if is_fallback else 0,
            priority=priority,
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def add_rule(self, *, playlist_id: int, rule_type: str, rule_value: str) -> PlaylistRule:
        rule = PlaylistRule(playlist_id=playlist_id, rule_type=rule_type, rule_value=rule_value)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def schedule_playlist(
        self,
        playlist_id: int,
        target: str,
        starts_at: datetime | None,
        ends_at: datetime | None,
        recurrence: str | None = None,
        priority: int = 100,
        timezone_name: str = "UTC",
    ) -> Schedule:
        starts_at, ends_at = self._validate_schedule_window(target, starts_at, ends_at)
        schedule = Schedule(
            playlist_id=playlist_id,
            target=target,
            starts_at=starts_at,
            ends_at=ends_at,
            recurrence=recurrence,
            priority=priority,
            timezone=timezone_name,
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def add_schedule_exception(
        self,
        *,
        schedule_id: int,
        starts_at: datetime,
        ends_at: datetime,
        reason: str | None = None,
    ) -> ScheduleException:
        starts_at = self._normalize(starts_at)
        ends_at = self._normalize(ends_at)
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValueError("invalid exception window")
        row = ScheduleException(
            schedule_id=schedule_id,
            starts_at=starts_at,
            ends_at=ends_at,
            reason=reason,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def add_blackout_window(
        self,
        *,
        target: str,
        starts_at: datetime,
        ends_at: datetime,
        reason: str | None = None,
    ) -> ScheduleBlackoutWindow:
        starts_at = self._normalize(starts_at)
        ends_at = self._normalize(ends_at)
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValueError("invalid blackout window")
        row = ScheduleBlackoutWindow(
            target=target,
            starts_at=starts_at,
            ends_at=ends_at,
            reason=reason,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _validate_schedule_window(
        self,
        target: str,
        starts_at: datetime | None,
        ends_at: datetime | None,
    ) -> tuple[datetime | None, datetime | None]:
        starts_at = self._normalize(starts_at)
        ends_at = self._normalize(ends_at)

        if starts_at and ends_at and ends_at <= starts_at:
            raise ValueError("ends_at must be after starts_at")

        return starts_at, ends_at

    def create_layout(self, name: str, definition_json: str) -> Layout:
        layout = Layout(name=name, definition_json=definition_json)
        self.db.add(layout)
        self.db.commit()
        self.db.refresh(layout)
        return layout

    def list_layouts(self) -> list[Layout]:
        return self.db.query(Layout).order_by(Layout.id.asc()).all()

    def _recurrence_matches(self, recurrence: str | None, now: datetime) -> bool:
        if not recurrence or recurrence in {"once", "daily"}:
            return True
        if recurrence.startswith("weekdays:"):
            values = recurrence.split(":", 1)[1]
            weekdays = {int(v.strip()) for v in values.split(",") if v.strip().isdigit()}
            return now.weekday() in weekdays
        return False

    def _is_blocked_by_exception(self, schedule_id: int, now: datetime) -> bool:
        rows = self.db.query(ScheduleException).filter(ScheduleException.schedule_id == schedule_id).all()
        for row in rows:
            starts_at = self._normalize(row.starts_at)
            ends_at = self._normalize(row.ends_at)
            if starts_at and ends_at and starts_at <= now <= ends_at:
                return True
        return False

    def _is_blocked_by_blackout(self, target: str, now: datetime) -> bool:
        rows = self.db.query(ScheduleBlackoutWindow).filter(ScheduleBlackoutWindow.target.in_([target, "all"])).all()
        for row in rows:
            starts_at = self._normalize(row.starts_at)
            ends_at = self._normalize(row.ends_at)
            if starts_at and ends_at and starts_at <= now <= ends_at:
                return True
        return False

    def resolve_active_playlist_id_at(self, target: str, at_time: datetime | None = None) -> int | None:
        now = self._normalize(at_time) or self._utc_now()
        if self._is_blocked_by_blackout(target, now):
            return None

        schedules = self.db.query(Schedule).filter(Schedule.target.in_([target, "all"])).all()

        active: list[Schedule] = []
        for sched in schedules:
            starts_at = self._normalize(sched.starts_at)
            ends_at = self._normalize(sched.ends_at)
            if starts_at and starts_at > now:
                continue
            if ends_at and ends_at < now:
                continue
            if not self._recurrence_matches(sched.recurrence, now):
                continue
            if self._is_blocked_by_exception(sched.id, now):
                continue
            active.append(sched)

        if not active:
            return None

        active.sort(
            key=lambda s: (
                0 if s.target == target else 1,
                -(s.priority or 100),
                self._normalize(s.starts_at) or datetime.min.replace(tzinfo=timezone.utc),
                s.id,
            ),
        )
        return active[0].playlist_id

    def resolve_active_playlist_id(self, target: str) -> int | None:
        return self.resolve_active_playlist_id_at(target, None)

    def validate_playlist_playable(self, playlist_id: int) -> bool:
        items = self.get_items(playlist_id)
        if not items:
            raise ValueError("playlist has no items")
        for item in items:
            if item.content_type in {"image", "video"} and item.media_id is None:
                raise ValueError("playlist contains media item without media_id")
            if item.content_type == "web_url" and not item.source_url:
                raise ValueError("playlist contains web_url item without source_url")
            if item.content_type == "widget" and not item.widget_config:
                raise ValueError("playlist contains widget item without widget_config")
        return True

    def resolve_for_device(self, device_id: str) -> dict:
        scheduled = self.resolve_active_playlist_id(device_id)
        if scheduled:
            self.validate_playlist_playable(scheduled)
            return {"playlist_id": scheduled, "source": "schedule"}

        device_assignments = (
            self.db.query(PlaylistAssignment)
            .filter(PlaylistAssignment.target_type == "device", PlaylistAssignment.target_id == device_id)
            .order_by(PlaylistAssignment.is_fallback.asc(), PlaylistAssignment.priority.asc(), PlaylistAssignment.id.asc())
            .all()
        )
        if device_assignments:
            first = device_assignments[0]
            self.validate_playlist_playable(first.playlist_id)
            return {"playlist_id": first.playlist_id, "source": "device_assignment", "fallback": bool(first.is_fallback)}

        group_ids = [
            str(row.group_id)
            for row in self.db.query(DeviceGroupMember).filter(DeviceGroupMember.device_id == device_id).all()
        ]
        if group_ids:
            group_assignments = (
                self.db.query(PlaylistAssignment)
                .filter(PlaylistAssignment.target_type == "group", PlaylistAssignment.target_id.in_(group_ids))
                .order_by(PlaylistAssignment.is_fallback.asc(), PlaylistAssignment.priority.asc(), PlaylistAssignment.id.asc())
                .all()
            )
            if group_assignments:
                first = group_assignments[0]
                self.validate_playlist_playable(first.playlist_id)
                return {"playlist_id": first.playlist_id, "source": "group_assignment", "fallback": bool(first.is_fallback)}

        return {"playlist_id": None, "source": "none"}


    def resolve_zone_playback_plan(self, device_id: str) -> list[dict]:
        layouts = self.list_layouts()
        if not layouts:
            return []

        # For now, pick first layout as active baseline.
        layout = layouts[0]
        preview = self.get_layout_preview(layout.id)
        zones: list[dict] = []
        fallback = self.resolve_for_device(device_id).get("playlist_id")

        for zone in preview.get("zones", []):
            playlist_id = zone.get("playlist_id") or fallback
            zones.append(
                {
                    "layout_id": layout.id,
                    "layout_name": layout.name,
                    "zone_id": zone["id"],
                    "zone_name": zone["name"],
                    "x": zone["x"],
                    "y": zone["y"],
                    "width": zone["width"],
                    "height": zone["height"],
                    "playlist_id": playlist_id,
                }
            )
        return zones

    def add_zone(
        self,
        *,
        layout_id: int,
        name: str,
        x: int = 0,
        y: int = 0,
        width: int = 1920,
        height: int = 1080,
    ) -> Zone:
        zone = Zone(layout_id=layout_id, name=name, x=x, y=y, width=width, height=height)
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def assign_zone_playlist(self, *, zone_id: int, playlist_id: int) -> ZonePlaylistAssignment:
        assignment = self.db.query(ZonePlaylistAssignment).filter(ZonePlaylistAssignment.zone_id == zone_id).first()
        if assignment:
            assignment.playlist_id = playlist_id
        else:
            assignment = ZonePlaylistAssignment(zone_id=zone_id, playlist_id=playlist_id)
            self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get_layout_preview(self, layout_id: int) -> dict:
        layout = self.db.query(Layout).filter(Layout.id == layout_id).first()
        if not layout:
            return {"layout": None, "zones": []}

        zones = self.db.query(Zone).filter(Zone.layout_id == layout_id).order_by(Zone.id.asc()).all()
        zone_ids = [z.id for z in zones]
        assignments = {}
        if zone_ids:
            for row in self.db.query(ZonePlaylistAssignment).filter(ZonePlaylistAssignment.zone_id.in_(zone_ids)).all():
                assignments[row.zone_id] = row.playlist_id

        return {
            "layout": {
                "id": layout.id,
                "name": layout.name,
                "definition_json": layout.definition_json,
            },
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "x": z.x,
                    "y": z.y,
                    "width": z.width,
                    "height": z.height,
                    "playlist_id": assignments.get(z.id),
                }
                for z in zones
            ],
        }
