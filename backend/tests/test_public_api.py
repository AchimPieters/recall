from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.config import get_settings
from backend.app.core.public_api_auth import reset_public_api_rate_limits_for_tests

client = TestClient(app)


def _set_public_keys(raw: str) -> None:
    get_settings.cache_clear()
    import os

    os.environ["RECALL_PUBLIC_API_KEYS"] = raw
    reset_public_api_rate_limits_for_tests()


def test_public_api_rejects_missing_key() -> None:
    _set_public_keys("public-key-1:tenant-a:5")
    response = client.get("/api/public/v1/health")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_public_api_accepts_valid_key_and_returns_tenant() -> None:
    _set_public_keys("public-key-1:tenant-a:5")
    response = client.get(
        "/api/public/v1/health",
        headers={"X-API-Key": "public-key-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tenant"] == "tenant-a"
    assert payload["version"] == "v1"


def test_public_api_enforces_tenant_rate_limit() -> None:
    _set_public_keys("public-key-1:tenant-a:1")
    first = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})
    second = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Public API tenant rate limit exceeded"


def test_public_api_rate_limit_is_shared_per_tenant_across_keys() -> None:
    _set_public_keys("public-key-1:tenant-a:2,public-key-2:tenant-a:2")

    first = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})
    second = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-2"})
    third = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Public API tenant rate limit exceeded"


def test_public_api_rate_limit_is_isolated_between_tenants() -> None:
    _set_public_keys("public-key-1:tenant-a:1,public-key-2:tenant-b:1")

    tenant_a_first = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})
    tenant_b_first = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-2"})
    tenant_a_second = client.get("/api/public/v1/health", headers={"X-API-Key": "public-key-1"})

    assert tenant_a_first.status_code == 200
    assert tenant_b_first.status_code == 200
    assert tenant_b_first.json()["tenant"] == "tenant-b"
    assert tenant_a_second.status_code == 429
