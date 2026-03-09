from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.models.security import (
    AuditLog,
    PasswordResetToken,
    RefreshToken,
    SecurityAuditEvent,
)


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

    def revoke_all_refresh_tokens_for_user(self, username: str) -> int:
        count = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.username == username, RefreshToken.revoked.is_(False))
            .update({RefreshToken.revoked: True}, synchronize_session=False)
        )
        self.db.commit()
        return int(count)

    def create_password_reset_token(
        self,
        *,
        username: str,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        record = PasswordResetToken(
            username=username,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_active_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        return (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )

    def mark_password_reset_token_used(self, token_hash: str, used_at: datetime) -> None:
        token = self.get_active_password_reset_token(token_hash)
        if token:
            token.used_at = used_at
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
        actor_type: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        organization_id: int | None = None,
    ) -> list[AuditLog]:
        query = self.db.query(AuditLog)
        if actor_type:
            query = query.filter(AuditLog.actor_type == actor_type)
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if ip_address:
            query = query.filter(AuditLog.ip_address == ip_address)
        if created_from:
            query = query.filter(AuditLog.created_at >= created_from)
        if created_to:
            query = query.filter(AuditLog.created_at <= created_to)
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
