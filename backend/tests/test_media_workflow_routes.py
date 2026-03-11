from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models.media import Media
from backend.app.models.settings import User

client = TestClient(app)


def _ensure_user(username: str, role: str, organization_id: int | None) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                password_hash=get_password_hash("MediaRoutePass1!"),
                role=role,
                organization_id=organization_id,
                is_active=True,
            )
            db.add(user)
        else:
            user.password_hash = get_password_hash("MediaRoutePass1!")
            user.role = role
            user.organization_id = organization_id
            user.is_active = True
        db.commit()
    finally:
        db.close()


def _create_media(organization_id: int, workflow_state: str = "draft") -> int:
    db = SessionLocal()
    try:
        media = Media(
            name=f"workflow-{organization_id}.png",
            path=f"/tmp/workflow-{organization_id}.png",
            mime_type="image/png",
            organization_id=organization_id,
            workflow_state=workflow_state,
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        return media.id
    finally:
        db.close()


def test_transition_returns_404_for_cross_org_media() -> None:
    _ensure_user("media-org1-admin", role="admin", organization_id=1)
    media_id = _create_media(organization_id=2)
    token = create_access_token(subject="media-org1-admin", role="admin")

    response = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "review"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "media not found"


def test_transition_rejects_invalid_target_state() -> None:
    _ensure_user("media-global-admin", role="admin", organization_id=None)
    media_id = _create_media(organization_id=3)
    token = create_access_token(subject="media-global-admin", role="admin")

    response = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "broken-state"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "unsupported workflow state" in response.json()["detail"]
