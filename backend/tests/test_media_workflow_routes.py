import json
from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models.event import Event
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


def test_editor_reviewer_publish_workflow_roles() -> None:
    _ensure_user("media-editor", role="editor", organization_id=7)
    _ensure_user("media-reviewer", role="reviewer", organization_id=7)
    media_id = _create_media(organization_id=7, workflow_state="draft")

    editor_token = create_access_token(subject="media-editor", role="editor")
    reviewer_token = create_access_token(subject="media-reviewer", role="reviewer")

    to_review = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "review"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert to_review.status_code == 200
    assert to_review.json()["workflow_state"] == "review"

    publish_as_editor = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "published"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert publish_as_editor.status_code == 403

    to_approved = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "approved"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert to_approved.status_code == 200
    assert to_approved.json()["workflow_state"] == "approved"

    to_published = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "published"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert to_published.status_code == 200
    assert to_published.json()["workflow_state"] == "published"


def test_reviewer_to_draft_requires_reason() -> None:
    _ensure_user("media-reviewer-draft", role="reviewer", organization_id=9)
    media_id = _create_media(organization_id=9, workflow_state="review")
    reviewer_token = create_access_token(
        subject="media-reviewer-draft", role="reviewer"
    )

    missing_reason = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "draft"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert missing_reason.status_code == 400
    assert "transition reason required" in missing_reason.json()["detail"]

    with_reason = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "draft", "reason": "Needs legal update"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["workflow_state"] == "draft"


def test_workflow_transition_writes_audit_event_payload() -> None:
    _ensure_user("media-reviewer-event", role="reviewer", organization_id=10)
    media_id = _create_media(organization_id=10, workflow_state="review")
    reviewer_token = create_access_token(
        subject="media-reviewer-event", role="reviewer"
    )

    response = client.post(
        f"/api/v1/media/{media_id}/workflow/transition",
        json={"state": "draft", "reason": "Needs translation review"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        event = (
            db.query(Event)
            .filter(
                Event.category == "media_workflow", Event.action == "state_transition"
            )
            .order_by(Event.id.desc())
            .first()
        )
        assert event is not None
        payload = json.loads(event.payload)
        assert payload["media_id"] == media_id
        assert payload["from_state"] == "review"
        assert payload["to_state"] == "draft"
        assert payload["reason"] == "Needs translation review"
    finally:
        db.close()
