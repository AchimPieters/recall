from pathlib import Path

from backend.app.core import events as event_registry
from backend.app.core.events.types import (
    ALERT_TRIGGERED,
    DEVICE_REGISTERED,
    MEDIA_UPLOADED,
    OTA_UPDATE_STARTED,
    PLAYLIST_UPDATED,
)


REQUIRED_EVENTS = {
    DEVICE_REGISTERED,
    PLAYLIST_UPDATED,
    MEDIA_UPLOADED,
    ALERT_TRIGGERED,
    OTA_UPDATE_STARTED,
}


def test_required_domain_events_have_worker_subscribers() -> None:
    handlers = event_registry.subscribers._handlers  # validated contract for registry wiring
    missing: list[str] = []
    for event_name in sorted(REQUIRED_EVENTS):
        event_handlers = handlers.get(event_name, [])
        if len(event_handlers) < 2:
            missing.append(f"{event_name}: expected >=2 subscribers, found {len(event_handlers)}")
    assert not missing, "Missing domain event wiring: " + " | ".join(missing)


def test_routes_do_not_import_domain_layer_directly() -> None:
    routes_dir = Path(__file__).resolve().parents[1] / "app" / "api" / "routes"
    violations: list[str] = []
    for path in sorted(routes_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        content = path.read_text(encoding="utf-8")
        if "backend.app.domain" in content:
            violations.append(str(path.relative_to(Path(__file__).resolve().parents[2])))
    assert not violations, "Routes must not import domain layer directly: " + ", ".join(violations)


def test_complex_services_depend_on_domain_layer() -> None:
    services_root = Path(__file__).resolve().parents[1] / "app" / "services"
    expected_imports = {
        "playlist_service.py": "from backend.app.domain import",
        "device_service.py": "from backend.app.domain import",
    }
    missing: list[str] = []
    for filename, needle in expected_imports.items():
        content = (services_root / filename).read_text(encoding="utf-8")
        if needle not in content:
            missing.append(f"{filename}: missing '{needle}'")
    assert not missing, "Domain layer dependency missing: " + " | ".join(missing)
