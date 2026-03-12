from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.api import main as main_module

client = TestClient(app)


def test_rejects_invalid_host_header(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module.settings_conf, "allowed_hosts", ["localhost", "testserver"]
    )

    response = client.get("/api/v1/health", headers={"Host": "evil.example.com"})

    assert response.status_code == 400
    assert response.text == "Invalid host header"


def test_enforce_https_rejects_plain_http_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(main_module.settings_conf, "environment", "prod")
    monkeypatch.setattr(main_module.settings_conf, "enforce_https", True)
    monkeypatch.setattr(main_module.settings_conf, "trust_forwarded_proto", False)
    monkeypatch.setattr(main_module.settings_conf, "allowed_hosts", ["testserver"])

    response = client.get("/api/v1/health")

    assert response.status_code == 426
    assert response.text == "HTTPS required"


def test_sets_hsts_when_https_enforced_and_forwarded_proto_trusted(monkeypatch) -> None:
    monkeypatch.setattr(main_module.settings_conf, "environment", "prod")
    monkeypatch.setattr(main_module.settings_conf, "enforce_https", True)
    monkeypatch.setattr(main_module.settings_conf, "trust_forwarded_proto", True)
    monkeypatch.setattr(main_module.settings_conf, "allowed_hosts", ["testserver"])

    response = client.get("/api/v1/health", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )
