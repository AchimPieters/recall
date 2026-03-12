from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
CACHE_MODULE = _load_module("recall_player_cache", ROOT / "agent_modules" / "cache.py")
WATCHDOG_MODULE = _load_module("recall_player_watchdog", ROOT / "agent_modules" / "watchdog.py")
AGENT_MODULE = _load_module("recall_player_agent", ROOT / "agent.py")


def test_cache_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CACHE_MODULE, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(
        CACHE_MODULE,
        "CONFIG_CACHE_PATH",
        (tmp_path / ".agent" / "device-config.json"),
    )

    payload = {"active_media_local_path": "/tmp/local.mp4", "heartbeat_interval": 30}
    CACHE_MODULE.write_cached_config(payload)
    loaded = CACHE_MODULE.read_cached_config()

    assert loaded == payload


def test_watchdog_backoff_caps_and_sleeps(monkeypatch) -> None:
    slept = {"value": 0.0}

    monkeypatch.setattr(WATCHDOG_MODULE.secrets, "randbelow", lambda _: 0)
    monkeypatch.setattr(
        WATCHDOG_MODULE.time,
        "sleep",
        lambda seconds: slept.__setitem__("value", seconds),
    )

    next_backoff = WATCHDOG_MODULE.backoff_sleep(120)
    assert slept["value"] == 120
    assert next_backoff == 120


def test_run_offline_plays_cached_media(monkeypatch, tmp_path: Path) -> None:
    media_path = tmp_path / "cached.mp4"
    media_path.write_bytes(b"x")

    monkeypatch.setattr(
        AGENT_MODULE,
        "read_cached_config",
        lambda: {"active_media_local_path": str(media_path)},
    )
    played = {"file": None}

    def _play(path: Path) -> dict[str, str]:
        played["file"] = str(path)
        return {"status": "ready", "file": str(path)}

    monkeypatch.setattr(AGENT_MODULE, "play_from_cache", _play)
    AGENT_MODULE.run_offline()

    assert played["file"] == str(media_path)
