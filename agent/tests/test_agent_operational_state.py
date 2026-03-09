import json
from pathlib import Path

from agent.agent_modules import cache
from agent.agent_modules.health import write_health
from agent.agent_modules.logs import append_log


def test_health_file_written(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / ".agent")
    import agent.agent_modules.health as health

    monkeypatch.setattr(health, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(health, "HEALTH_PATH", (tmp_path / ".agent" / "health.json"))

    write_health("online", "ok")
    payload = json.loads((tmp_path / ".agent" / "health.json").read_text(encoding="utf-8"))
    assert payload["status"] == "online"


def test_log_append_writes_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / ".agent")
    import agent.agent_modules.logs as logs

    monkeypatch.setattr(logs, "CACHE_DIR", tmp_path / ".agent")
    monkeypatch.setattr(logs, "LOG_PATH", (tmp_path / ".agent" / "agent.log"))

    append_log("info", "boot")
    append_log("warning", "retry")
    content = (tmp_path / ".agent" / "agent.log").read_text(encoding="utf-8")
    assert "boot" in content
    assert "retry" in content
