from sqlalchemy.orm import Session

from backend.app.models.event import Event


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        category: str,
        action: str,
        actor: str,
        payload: str,
        organization_id: int | None,
    ) -> Event:
        event = Event(
            category=category,
            action=action,
            actor=actor,
            payload=payload,
            organization_id=organization_id,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def recent(
        self, limit: int = 100, organization_id: int | None = None
    ) -> list[Event]:
        query = self.db.query(Event)
        if organization_id is not None:
            query = query.filter(Event.organization_id == organization_id)
        return query.order_by(Event.created_at.desc()).limit(limit).all()
