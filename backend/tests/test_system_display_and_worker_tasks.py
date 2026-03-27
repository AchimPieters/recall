from __future__ import annotations

import subprocess
from types import SimpleNamespace

from backend.app.services.display_service import DisplayService
from backend.app.services.system_service import SystemService
from backend.app.workers import tasks as worker_tasks


class _FakeDB:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commit_calls = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.commit_calls += 1


def test_system_service_reboot_requires_confirmation() -> None:
    db = _FakeDB()
    service = SystemService(db)

    result = service.reboot(confirmed=False, actor="admin")

    assert result == {"ok": False, "reason": "confirmation_required"}
    assert db.commit_calls == 0


def test_system_service_reboot_timeout(monkeypatch) -> None:
    db = _FakeDB()
    service = SystemService(db)
    monkeypatch.setattr(service.events, "publish", lambda **_: None)

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="systemctl reboot", timeout=15)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    result = service.reboot(confirmed=True, actor="ops")

    assert result["ok"] is False
    assert "timed out" in result["stderr"]
    assert db.commit_calls == 1


def test_system_service_update_returns_subprocess_result(monkeypatch) -> None:
    db = _FakeDB()
    service = SystemService(db)
    monkeypatch.setattr(service.events, "publish", lambda **_: None)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="updated\n",
            stderr="",
        ),
    )

    result = service.update(confirmed=True, actor="admin")

    assert result == {"ok": True, "stdout": "updated", "stderr": ""}
    assert db.commit_calls == 1


def test_system_service_update_timeout(monkeypatch) -> None:
    db = _FakeDB()
    service = SystemService(db)
    monkeypatch.setattr(service.events, "publish", lambda **_: None)

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="/opt/recall/update.sh", timeout=300)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    result = service.update(confirmed=True, actor="ops")

    assert result["ok"] is False
    assert "timed out" in result["stderr"]


def test_display_service_detect_success(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="HDMI-1 connected primary\nDP-1 disconnected\n",
            stderr="",
        ),
    )

    result = DisplayService.detect()

    assert result == {"ok": True, "outputs": ["HDMI-1 connected primary"]}


def test_display_service_detect_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="xrandr failed\n",
        ),
    )

    result = DisplayService.detect()

    assert result == {"ok": False, "error": "xrandr failed"}


def test_worker_tasks_refresh_device_statuses(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    fake_session = _FakeSession()

    class _FakeDeviceService:
        def __init__(self, db) -> None:
            assert db is fake_session

        def mark_presence(self) -> int:
            return 7

    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(worker_tasks, "DeviceService", _FakeDeviceService)

    assert worker_tasks.refresh_device_statuses() == 7
    assert fake_session.closed is True
    assert worker_tasks.refresh_device_statuses_task() == 7


def test_worker_tasks_secret_rotation(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeSecretRotationService:
        def evaluate(self, *, last_rotated_at):
            captured["last_rotated_at"] = last_rotated_at
            return {"status": "ok", "age_days": 0}

    monkeypatch.setattr(
        worker_tasks.settings,
        "jwt_secret_last_rotated_at",
        "2026-03-01T00:00:00Z",
    )
    monkeypatch.setattr(worker_tasks, "SecretRotationService", _FakeSecretRotationService)

    assert worker_tasks.evaluate_secret_rotation() == {"status": "ok", "age_days": 0}
    assert captured["last_rotated_at"] == "2026-03-01T00:00:00Z"
    assert worker_tasks.evaluate_secret_rotation_task() == {"status": "ok", "age_days": 0}


def test_retryable_task_defaults() -> None:
    assert worker_tasks.RetryableTask.retry_backoff is True
    assert worker_tasks.RetryableTask.retry_jitter is True
    assert worker_tasks.RetryableTask.retry_kwargs["max_retries"] >= 1
