from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.models.security import AuditLog, RefreshToken, SecurityAuditEvent


class SecurityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_refresh_token(
        self, username: str, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        record = RefreshToken(
            username=username,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_active_refresh_token(self, token_hash: str) -> RefreshToken | None:
        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False)
            )
            .first()
        )

    def revoke_refresh_token(self, token_hash: str) -> None:
        token = self.get_active_refresh_token(token_hash)
        if token:
            token.revoked = True
            self.db.commit()

    def add_security_event(
        self, actor: str, event_type: str, detail: str, ip_address: str | None
    ) -> SecurityAuditEvent:
        event = SecurityAuditEvent(
            actor=actor,
            event_type=event_type,
            detail=detail,
            ip_address=ip_address,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event


    def add_audit_log(
        self,
        *,
        actor_type: str,
        actor_id: str,
        organization_id: int | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        before_state: str | None = None,
        after_state: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_audit_logs(
        self,
        *,
        limit: int = 100,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        organization_id: int | None = None,
    ) -> list[AuditLog]:
        query = self.db.query(AuditLog)
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if organization_id is not None:
            query = query.filter(AuditLog.organization_id == organization_id)
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    def list_security_events(
        self,
        limit: int = 100,
        actor: str | None = None,
        event_type: str | None = None,
    ) -> list[SecurityAuditEvent]:
        query = self.db.query(SecurityAuditEvent)
        if actor:
            query = query.filter(SecurityAuditEvent.actor == actor)
        if event_type:
            query = query.filter(SecurityAuditEvent.event_type == event_type)
        return query.order_by(SecurityAuditEvent.created_at.desc()).limit(limit).all()
