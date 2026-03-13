from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.repositories.security_repository import SecurityRepository


class SecurityService:
    def __init__(self, db: Session):
        self.repo = SecurityRepository(db)

    def list_security_events(
        self,
        *,
        limit: int = 100,
        actor: str | None = None,
        event_type: str | None = None,
    ):
        return self.repo.list_security_events(
            limit=max(1, min(limit, 500)),
            actor=actor,
            event_type=event_type,
        )

    def list_audit_logs(
        self,
        *,
        limit: int = 100,
        actor_type: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        organization_id: int | None = None,
    ):
        return self.repo.list_audit_logs(
            limit=max(1, min(limit, 500)),
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            created_from=created_from,
            created_to=created_to,
            organization_id=organization_id,
        )
