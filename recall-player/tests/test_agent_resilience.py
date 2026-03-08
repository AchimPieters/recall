from pathlib import Path

from agent_modules import cache
from agent_modules.watchdog import backoff_sleep
from agent import run_offline


def test_cache_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(
        cache, "CONFIG_CACHE_PATH", (tmp_path / ".agent" / "device-config.json")
    )

    payload = {"active_media_local_path": "/tmp/local.mp4", "heartbeat_interval": 30}
    cache.write_cached_config(payload)
    loaded = cache.read_cached_config()

    assert loaded == payload


def test_watchdog_backoff_caps_and_sleeps(monkeypatch) -> None:
    slept = {"value": 0.0}

    monkeypatch.setattr("agent_modules.watchdog.secrets.randbelow", lambda _: 0)
    monkeypatch.setattr(
        "agent_modules.watchdog.time.sleep",
        lambda seconds: slept.__setitem__("value", seconds),
    )

    next_backoff = backoff_sleep(120)
    assert slept["value"] == 120
    assert next_backoff == 120


def test_run_offline_plays_cached_media(monkeypatch, tmp_path: Path) -> None:
    media_path = tmp_path / "cached.mp4"
    media_path.write_bytes(b"x")

    monkeypatch.setattr(
        "agent.read_cached_config", lambda: {"active_media_local_path": str(media_path)}
    )
    played = {"file": None}

    def _play(path: Path) -> dict[str, str]:
        played["file"] = str(path)
        return {"status": "ready", "file": str(path)}

    monkeypatch.setattr("agent.play_from_cache", _play)
    run_offline()

    assert played["file"] == str(media_path)
