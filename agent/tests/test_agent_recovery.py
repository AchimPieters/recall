import json
from pathlib import Path

from agent.agent_modules import cache
from agent.agent_modules import recovery


def test_record_failure_and_trigger(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(recovery, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(recovery, "RECOVERY_PATH", (tmp_path / ".agent" / "recovery.json"))

    for _ in range(5):
        recovery.record_failure(window_minutes=30)

    payload = json.loads((tmp_path / ".agent" / "recovery.json").read_text(encoding="utf-8"))
    assert len(payload["failures"]) == 5
    assert recovery.should_trigger_recovery(max_failures=5, window_minutes=30)


def test_clear_failures_resets_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(recovery, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(recovery, "RECOVERY_PATH", (tmp_path / ".agent" / "recovery.json"))

    recovery.record_failure(window_minutes=30)
    recovery.clear_failures()

    payload = json.loads((tmp_path / ".agent" / "recovery.json").read_text(encoding="utf-8"))
    assert payload["failures"] == []
