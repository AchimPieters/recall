from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.repositories.security_repository import SecurityRepository


class AuthSecurityService:
    """Auth-focused facade over security repository operations."""

    def __init__(self, db: Session):
        self.repo = SecurityRepository(db)

    def create_refresh_token(
        self, username: str, token_hash: str, expires_at: datetime
    ):
        return self.repo.create_refresh_token(username, token_hash, expires_at)

    def get_active_refresh_token(self, token_hash: str):
        return self.repo.get_active_refresh_token(token_hash)

    def revoke_refresh_token(self, token_hash: str) -> None:
        self.repo.revoke_refresh_token(token_hash)

    def revoke_all_refresh_tokens_for_user(self, username: str) -> int:
        return self.repo.revoke_all_refresh_tokens_for_user(username)

    def create_password_reset_token(
        self,
        *,
        username: str,
        token_hash: str,
        expires_at: datetime,
    ):
        return self.repo.create_password_reset_token(
            username=username,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def get_active_password_reset_token(self, token_hash: str):
        return self.repo.get_active_password_reset_token(token_hash)

    def mark_password_reset_token_used(self, token_hash: str, used_at: datetime) -> None:
        self.repo.mark_password_reset_token_used(token_hash, used_at)

    def add_security_event(
        self, actor: str, event_type: str, detail: str, ip_address: str | None
    ):
        return self.repo.add_security_event(actor, event_type, detail, ip_address)

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
    ):
        return self.repo.add_audit_log(
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

    def list_security_events(
        self,
        *,
        limit: int = 100,
        actor: str | None = None,
        event_type: str | None = None,
    ):
        return self.repo.list_security_events(
            limit=max(1, min(limit, 500)), actor=actor, event_type=event_type
        )
