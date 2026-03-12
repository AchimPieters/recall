import os
from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import User


client = TestClient(app)


def _ensure_user(username: str, role: str = "admin") -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash="x", role=role)
            db.add(user)
            db.commit()
    finally:
        db.close()


def test_provisioning_token_and_enroll_flow() -> None:
    _ensure_user("prov-admin", role="admin")
    token = create_access_token(subject="prov-admin", role="admin")

    create_resp = client.post(
        "/api/v1/device/provisioning/token",
        json={"expires_in_minutes": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    provisioning_token = create_resp.json()["token"]

    enroll = client.post(
        "/api/v1/device/provision/enroll",
        json={
            "provisioning_token": provisioning_token,
            "id": "provisioned-device-1",
            "name": "Provisioned Device",
            "version": "1.2.3",
        },
        headers={"X-Device-Protocol-Version": "1"},
    )
    assert enroll.status_code == 200
    assert enroll.json()["device_id"] == "provisioned-device-1"
    assert "certificate" in enroll.json()


def test_provisioning_token_single_use() -> None:
    _ensure_user("prov-admin-2", role="admin")
    token = create_access_token(subject="prov-admin-2", role="admin")

    create_resp = client.post(
        "/api/v1/device/provisioning/token",
        json={"expires_in_minutes": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    provisioning_token = create_resp.json()["token"]

    payload = {
        "provisioning_token": provisioning_token,
        "id": "provisioned-device-2",
        "name": "Provisioned Device 2",
    }
    first = client.post("/api/v1/device/provision/enroll", json=payload)
    assert first.status_code == 200

    second = client.post(
        "/api/v1/device/provision/enroll",
        json={**payload, "id": "provisioned-device-3"},
    )
    assert second.status_code == 400
    assert "invalid or expired provisioning token" in second.json()["detail"]


def test_device_api_requires_certificate_when_enabled() -> None:
    os.environ["RECALL_DEVICE_API_REQUIRE_CERTIFICATE"] = "true"
    get_settings.cache_clear()
    from backend.app.api.routes import devices as devices_route

    devices_route.settings_conf = get_settings()

    try:
        _ensure_user("prov-admin-cert", role="admin")
        token = create_access_token(subject="prov-admin-cert", role="admin")

        create_resp = client.post(
            "/api/v1/device/provisioning/token",
            json={"expires_in_minutes": 60},
            headers={"Authorization": f"Bearer {token}"},
        )
        provisioning_token = create_resp.json()["token"]

        enroll = client.post(
            "/api/v1/device/provision/enroll",
            json={
                "provisioning_token": provisioning_token,
                "id": "provisioned-device-cert",
                "name": "Provisioned Device Cert",
            },
            headers={"X-Device-Protocol-Version": "1"},
        )
        assert enroll.status_code == 200
        fingerprint = enroll.json()["certificate_fingerprint"]

        missing_header = client.post(
            "/api/v1/device/heartbeat",
            json={"id": "provisioned-device-cert", "metrics": {"state": "ok"}},
            headers={"Authorization": f"Bearer {token}", "X-Device-Protocol-Version": "1"},
        )
        assert missing_header.status_code == 401
        assert missing_header.json()["detail"] == "Device certificate fingerprint required"

        ok = client.post(
            "/api/v1/device/heartbeat",
            json={"id": "provisioned-device-cert", "metrics": {"state": "ok"}},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok.status_code == 200

        missing_config = client.get(
            "/api/v1/device/config",
            params={"device_id": "provisioned-device-cert"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_config.status_code == 401

        ok_config = client.get(
            "/api/v1/device/config",
            params={"device_id": "provisioned-device-cert"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_config.status_code == 200

        missing_logs = client.post(
            "/api/v1/device/logs",
            json={
                "id": "provisioned-device-cert",
                "level": "info",
                "action": "log",
                "message": "hello",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_logs.status_code == 401

        ok_logs = client.post(
            "/api/v1/device/logs",
            json={
                "id": "provisioned-device-cert",
                "level": "info",
                "action": "log",
                "message": "hello",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_logs.status_code == 200

        missing_metrics = client.post(
            "/api/v1/device/metrics",
            json={"id": "provisioned-device-cert", "metrics": {"temperature": 42}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_metrics.status_code == 401

        ok_metrics = client.post(
            "/api/v1/device/metrics",
            json={"id": "provisioned-device-cert", "metrics": {"temperature": 42}},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_metrics.status_code == 200

        missing_commands = client.get(
            "/api/v1/device/commands",
            params={"device_id": "provisioned-device-cert"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
            },
        )
        assert missing_commands.status_code == 401

        ok_commands = client.get(
            "/api/v1/device/commands",
            params={"device_id": "provisioned-device-cert"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_commands.status_code == 200

        enqueue_command = client.post(
            "/api/v1/device/commands/enqueue",
            json={
                "device_id": "provisioned-device-cert",
                "command_type": "reload",
                "payload": {"reason": "test"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert enqueue_command.status_code == 200
        command_id = enqueue_command.json()["command_id"]

        missing_ack = client.post(
            "/api/v1/device/command-ack",
            json={
                "id": "provisioned-device-cert",
                "command_id": command_id,
                "status": "ok",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
            },
        )
        assert missing_ack.status_code == 401

        ok_ack = client.post(
            "/api/v1/device/command-ack",
            json={
                "id": "provisioned-device-cert",
                "command_id": command_id,
                "status": "ok",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_ack.status_code == 200

        missing_playback = client.post(
            "/api/v1/device/playback-status",
            json={"id": "provisioned-device-cert", "state": "idle"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
            },
        )
        assert missing_playback.status_code == 401

        ok_playback = client.post(
            "/api/v1/device/playback-status",
            json={"id": "provisioned-device-cert", "state": "idle"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Device-Protocol-Version": "1",
                "X-Device-Certificate-Fingerprint": fingerprint,
            },
        )
        assert ok_playback.status_code == 200
    finally:
        os.environ["RECALL_DEVICE_API_REQUIRE_CERTIFICATE"] = "false"
        get_settings.cache_clear()
        devices_route.settings_conf = get_settings()
