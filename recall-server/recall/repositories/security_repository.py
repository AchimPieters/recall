from datetime import datetime

from sqlalchemy.orm import Session

from recall.models.security import RefreshToken, SecurityAuditEvent


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
            .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
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
