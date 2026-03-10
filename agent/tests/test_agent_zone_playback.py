from agent.agent import play_zone_plan


def test_play_zone_plan_writes_zone_logs(monkeypatch) -> None:
    messages: list[str] = []

    monkeypatch.setattr("agent.agent.append_log", lambda level, msg: messages.append(f"{level}:{msg}"))

    play_zone_plan(
        {
            "zone_plan": [
                {"zone_name": "left", "playlist_id": 1},
                {"zone_name": "right", "playlist_id": 2},
            ]
        }
    )

    assert any("zone_plan_received" in m for m in messages)
    assert any("zone=left" in m for m in messages)
    assert any("zone=right" in m for m in messages)
