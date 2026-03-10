from agent import agent


def test_recovery_policy_uses_configured_thresholds(monkeypatch) -> None:
    monkeypatch.setattr(agent.config, "RECOVERY_WINDOW_MINUTES", 15)
    monkeypatch.setattr(agent.config, "RECOVERY_MAX_FAILURES", 7)

    called: dict[str, int] = {}

    def fake_should_trigger_recovery(*, max_failures: int, window_minutes: int) -> bool:
        called["max_failures"] = max_failures
        called["window_minutes"] = window_minutes
        return True

    monkeypatch.setattr(agent, "should_trigger_recovery", fake_should_trigger_recovery)

    assert agent._should_trigger_recovery_with_policy() is True
    assert called == {"max_failures": 7, "window_minutes": 15}


def test_recovery_policy_clamps_invalid_thresholds(monkeypatch) -> None:
    monkeypatch.setattr(agent.config, "RECOVERY_WINDOW_MINUTES", 0)
    monkeypatch.setattr(agent.config, "RECOVERY_MAX_FAILURES", 0)

    called: dict[str, int] = {}

    def fake_record_failure(*, window_minutes: int) -> int:
        called["window_minutes"] = window_minutes
        return 1

    def fake_should_trigger_recovery(*, max_failures: int, window_minutes: int) -> bool:
        called["max_failures"] = max_failures
        called["window_minutes_should"] = window_minutes
        return False

    monkeypatch.setattr(agent, "record_failure", fake_record_failure)
    monkeypatch.setattr(agent, "should_trigger_recovery", fake_should_trigger_recovery)

    assert agent._record_failure_with_policy() == 1
    assert agent._should_trigger_recovery_with_policy() is False
    assert called["window_minutes"] == 1
    assert called["max_failures"] == 1
    assert called["window_minutes_should"] == 1
