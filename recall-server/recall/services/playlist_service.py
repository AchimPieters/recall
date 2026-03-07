from datetime import datetime, timezone
from sqlalchemy.orm import Session

from recall.models.media import Playlist, PlaylistItem, Schedule


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
            max_position = (
                self.db.query(PlaylistItem)
                .filter(PlaylistItem.playlist_id == playlist_id)
                .count()
            )
            position = max_position

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

    def schedule_playlist(
        self,
        playlist_id: int,
        target: str,
        starts_at: datetime | None,
        ends_at: datetime | None,
    ) -> Schedule:
        schedule = Schedule(
            playlist_id=playlist_id,
            target=target,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def resolve_active_playlist_id(self, target: str) -> int | None:
        now = self._utc_now()
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
                self._normalize(s.starts_at) or datetime.min.replace(tzinfo=timezone.utc),
                s.id,
            ),
            reverse=True,
        )
        return active[0].playlist_id
