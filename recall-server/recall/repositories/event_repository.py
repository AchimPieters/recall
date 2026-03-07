from sqlalchemy.orm import Session

from recall.models.event import Event


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, category: str, action: str, actor: str, payload: str) -> Event:
        event = Event(category=category, action=action, actor=actor, payload=payload)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def recent(self, limit: int = 100) -> list[Event]:
        return self.db.query(Event).order_by(Event.created_at.desc()).limit(limit).all()
