from pathlib import Path


def test_compose_stack_includes_required_phase3_services() -> None:
    compose = (
        Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml"
    ).read_text(encoding="utf-8")

    required_services = [
        "recall-api:",
        "recall-worker:",
        "recall-frontend:",
        "postgres:",
        "redis:",
        "recall-agent:",
    ]
    missing = [service for service in required_services if service not in compose]
    assert not missing, "Compose stack missing required services: " + ", ".join(missing)

    assert "RECALL_SERVER_URL: http://recall-api:8000" in compose
