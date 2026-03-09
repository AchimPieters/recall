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
        media_id: int,
        position: int | None = None,
        duration_seconds: int | None = None,
    ) -> PlaylistItem:
        if position is None:
            position = (
                self.db.query(PlaylistItem)
                .filter(PlaylistItem.playlist_id == playlist_id)
                .count()
            )

        item = PlaylistItem(
            playlist_id=playlist_id,
            media_id=media_id,
            position=position,
            duration_seconds=duration_seconds,
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

        # Overlaps are allowed; conflict resolution happens via priority at runtime.
        return starts_at, ends_at

    def create_layout(self, name: str, definition_json: str) -> Layout:
        layout = Layout(name=name, definition_json=definition_json)
        self.db.add(layout)
        self.db.commit()
        self.db.refresh(layout)
        return layout

    def list_layouts(self) -> list[Layout]:
        return self.db.query(Layout).order_by(Layout.id.asc()).all()

    def resolve_active_playlist_id_at(self, target: str, at_time: datetime | None = None) -> int | None:
        now = self._normalize(at_time) or self._utc_now()
        schedules = self.db.query(Schedule).filter(Schedule.target.in_([target, "all"])).all()

        active: list[Schedule] = []
        for sched in schedules:
            starts_at = self._normalize(sched.starts_at)
            ends_at = self._normalize(sched.ends_at)
            if starts_at and starts_at > now:
                continue
            if ends_at and ends_at < now:
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

    def resolve_for_device(self, device_id: str) -> dict:
        # 1) schedule has precedence
        scheduled = self.resolve_active_playlist_id(device_id)
        if scheduled:
            return {"playlist_id": scheduled, "source": "schedule"}

        # 2) direct device assignment
        device_assignments = (
            self.db.query(PlaylistAssignment)
            .filter(PlaylistAssignment.target_type == "device", PlaylistAssignment.target_id == device_id)
            .order_by(PlaylistAssignment.is_fallback.asc(), PlaylistAssignment.priority.asc(), PlaylistAssignment.id.asc())
            .all()
        )
        if device_assignments:
            first = device_assignments[0]
            return {"playlist_id": first.playlist_id, "source": "device_assignment", "fallback": bool(first.is_fallback)}

        # 3) group assignment
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
                return {"playlist_id": first.playlist_id, "source": "group_assignment", "fallback": bool(first.is_fallback)}

        return {"playlist_id": None, "source": "none"}
