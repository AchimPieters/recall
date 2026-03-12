from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models.media import Media, MediaVersion, Playlist, PlaylistItem
from backend.app.services.device_service import DeviceService
from backend.app.services.playlist_service import PlaylistService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_device_tags_and_filters() -> None:
    db = _db_session()
    svc = DeviceService(db)

    svc.register("d1", "Device 1", None, "1.0.0", organization_id=1)
    svc.register("d2", "Device 2", None, "1.0.1", organization_id=1)
    svc.assign_tag("d1", "lobby", organization_id=1)

    tagged = svc.list_devices(organization_id=1, tag="lobby")
    assert [d.id for d in tagged] == ["d1"]

    by_version = svc.list_devices(organization_id=1, version="1.0.1")
    assert [d.id for d in by_version] == ["d2"]


def test_device_group_filter_and_last_seen_filter() -> None:
    db = _db_session()
    svc = DeviceService(db)

    d1 = svc.register("g1", "Group Device", None, "1.0.0", organization_id=1)
    d2 = svc.register("g2", "Other Device", None, "1.0.0", organization_id=1)

    group = svc.create_group("Store-1", organization_id=1)
    svc.assign_group_member(group.id, d1.id)

    in_group = svc.list_devices(organization_id=1, group_id=group.id)
    assert [d.id for d in in_group] == ["g1"]

    d2.last_seen = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db.commit()

    stale = svc.list_devices(
        organization_id=1,
        last_seen_before=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )
    assert [d.id for d in stale] == ["g2"]


def test_group_bulk_action_rollout_percentage_selects_subset() -> None:
    db = _db_session()
    svc = DeviceService(db)

    d1 = svc.register("r1", "Rollout 1", None, "1.1.0", organization_id=1)
    d2 = svc.register("r2", "Rollout 2", None, "1.1.0", organization_id=1)
    d3 = svc.register("r3", "Rollout 3", None, "1.1.0", organization_id=1)
    d4 = svc.register("r4", "Rollout 4", None, "1.1.0", organization_id=1)

    group = svc.create_group("RolloutGroup", organization_id=1)
    for device in (d1, d2, d3, d4):
        svc.assign_group_member(group.id, device.id)

    result = svc.execute_group_action(
        group_id=group.id,
        action="update",
        actor="admin",
        organization_id=1,
        target_version="1.2.0",
        rollout_percentage=50,
    )

    assert result["accepted"] == 2
    assert len(result["deferred_device_ids"]) == 2


def test_group_bulk_action_rejects_incompatible_target_version() -> None:
    db = _db_session()
    svc = DeviceService(db)

    dev = svc.register("cmp-1", "Compat Device", None, "1.4.0", organization_id=1)
    group = svc.create_group("CompatGroup", organization_id=1)
    svc.assign_group_member(group.id, dev.id)

    try:
        svc.execute_group_action(
            group_id=group.id,
            action="update",
            actor="admin",
            organization_id=1,
            target_version="2.0.0",
        )
        assert False, "expected ValueError for incompatible version"
    except ValueError as exc:
        assert "incompatible target_version" in str(exc)


def test_group_bulk_action_dry_run_does_not_emit_logs_or_events() -> None:
    db = _db_session()
    svc = DeviceService(db)

    dev = svc.register("dry-1", "Dry Run Device", None, "1.2.0", organization_id=1)
    group = svc.create_group("DryRun", organization_id=1)
    svc.assign_group_member(group.id, dev.id)

    result = svc.execute_group_action(
        group_id=group.id,
        action="update",
        actor="admin",
        organization_id=1,
        target_version="1.3.0",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert "event_id" not in result


def test_device_config_includes_active_media_path_and_checksum() -> None:
    db = _db_session()
    svc = DeviceService(db)

    svc.register("cfg-1", "Config Device", None, "1.0.0", organization_id=1)

    media = Media(
        organization_id=1, name="Poster", path="media/poster.png", mime_type="image/png"
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    version = MediaVersion(
        media_id=media.id, version=1, path="media/poster-v1.png", checksum="abc123"
    )
    db.add(version)

    playlist = Playlist(name="Device Playlist")
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    db.add(
        PlaylistItem(
            playlist_id=playlist.id, media_id=media.id, content_type="image", position=0
        )
    )
    db.commit()

    PlaylistService(db).add_assignment(
        playlist_id=playlist.id, target_type="device", target_id="cfg-1"
    )

    config = svc.get_config("cfg-1")
    assert config["active_playlist_id"] == playlist.id
    assert config["active_media_id"] == media.id
    assert config["active_media_path"] == "media/poster-v1.png"
    assert config["active_media_checksum"] == "abc123"


def test_group_rollback_rejects_unknown_target_version() -> None:
    db = _db_session()
    svc = DeviceService(db)

    d1 = svc.register("rb-1", "Rollback 1", None, "1.4.0", organization_id=1)
    d2 = svc.register("rb-2", "Rollback 2", None, "1.5.0", organization_id=1)

    group = svc.create_group("RollbackGroup", organization_id=1)
    for device in (d1, d2):
        svc.assign_group_member(group.id, device.id)

    try:
        svc.execute_group_action(
            group_id=group.id,
            action="rollback",
            actor="admin",
            organization_id=1,
            target_version="1.3.0",
        )
        assert False, "expected ValueError for unknown rollback target version"
    except ValueError as exc:
        assert "unknown rollback target_version" in str(exc)
