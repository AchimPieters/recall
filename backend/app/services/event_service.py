import json
from typing import Any

from sqlalchemy.orm import Session

from backend.app.repositories import EventRepository


class EventService:
    def __init__(self, db: Session):
        self.repo = EventRepository(db)

    def publish(
        self,
        category: str,
        action: str,
        actor: str,
        payload: dict[str, Any],
        organization_id: int | None = None,
    ) -> dict:
        event = self.repo.create(
            category=category,
            action=action,
            actor=actor,
            payload=json.dumps(payload, sort_keys=True),
            organization_id=organization_id,
        )
        return {
            "id": event.id,
            "category": event.category,
            "action": event.action,
            "actor": event.actor,
            "organization_id": event.organization_id,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }

    def list_recent(
        self, limit: int = 100, organization_id: int | None = None
    ) -> list[dict]:
        events = self.repo.recent(limit=limit, organization_id=organization_id)
        return [
            {
                "id": e.id,
                "category": e.category,
                "action": e.action,
                "actor": e.actor,
                "organization_id": e.organization_id,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
