from fastapi.testclient import TestClient

from recall.api.main import app


client = TestClient(app)


def test_app_boot_and_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
