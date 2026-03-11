from datetime import datetime, timedelta, timezone
import json
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.core.config import get_settings
from backend.app.core.mfa import generate_recovery_codes, generate_totp_secret, verify_totp_code
from backend.app.core.security import (
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    parse_mfa_token,
    parse_refresh_token,
    validate_password_policy,
    verify_password,
)
from backend.app.db.database import get_db
from backend.app.models import User
from backend.app.repositories.security_repository import SecurityRepository

router = APIRouter(tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
settings_conf = get_settings()

failed_login_attempts: dict[str, list[datetime]] = {}
failed_login_lock = Lock()
failed_mfa_verify_attempts: dict[str, list[datetime]] = {}
failed_mfa_verify_lock = Lock()
failed_mfa_setup_attempts: dict[str, list[datetime]] = {}
failed_mfa_setup_lock = Lock()


class RefreshPayload(BaseModel):
    refresh_token: str


class LogoutPayload(BaseModel):
    refresh_token: str


class PasswordResetRequestPayload(BaseModel):
    username: str = Field(min_length=1, max_length=255)


class PasswordResetConfirmPayload(BaseModel):
    reset_token: str = Field(min_length=16, max_length=2048)
    new_password: str = Field(min_length=8, max_length=512)


class ActivateUserPayload(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    active: bool = True


class MFASetupPayload(BaseModel):
    regenerate: bool = False
    code: str | None = Field(default=None, min_length=6, max_length=32)


class MFAVerifyPayload(BaseModel):
    mfa_token: str | None = Field(default=None, min_length=8, max_length=4096)
    code: str | None = Field(default=None, min_length=6, max_length=32)
    recovery_code: str | None = Field(default=None, min_length=6, max_length=64)




def _hash_recovery_codes(codes: list[str]) -> list[str]:
    return [hash_token(code.strip().lower()) for code in codes]


def _verify_recovery_code(user: User, recovery_code: str | None) -> bool:
    if not recovery_code or not user.mfa_recovery_codes:
        return False
    try:
        hashes = json.loads(user.mfa_recovery_codes)
    except json.JSONDecodeError:
        return False
    candidate = hash_token(recovery_code.strip().lower())
    if candidate not in hashes:
        return False
    hashes = [h for h in hashes if h != candidate]
    user.mfa_recovery_codes = json.dumps(hashes, sort_keys=True)
    return True


def _require_mfa_for_user(user: User) -> bool:
    return (user.role or '').strip().lower() == 'admin'

def bootstrap_admin(db: Session) -> None:
    admin = (
        db.query(User)
        .filter(User.username == settings_conf.bootstrap_admin_username)
        .first()
    )
    password = settings_conf.bootstrap_admin_password.strip()
    if admin or not password:
        return

    validate_password_policy(password)

    db.add(
        User(
            username=settings_conf.bootstrap_admin_username,
            password_hash=get_password_hash(password),
            role="admin",
            is_active=True,
        )
    )
    db.commit()


def _utc_normalized(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _prune_failed_attempts(username: str, now: datetime) -> list[datetime]:
    window = timedelta(minutes=settings_conf.auth_lockout_minutes)
    attempts = failed_login_attempts.get(username, [])
    pruned = [attempt for attempt in attempts if now - attempt < window]
    if pruned:
        failed_login_attempts[username] = pruned
    else:
        failed_login_attempts.pop(username, None)
    return pruned


def _is_locked_out(username: str, now: datetime) -> bool:
    with failed_login_lock:
        attempts = _prune_failed_attempts(username, now)
        return len(attempts) >= settings_conf.auth_lockout_threshold


def _record_failed_login(username: str, now: datetime) -> None:
    with failed_login_lock:
        attempts = _prune_failed_attempts(username, now)
        attempts.append(now)
        failed_login_attempts[username] = attempts


def _clear_failed_logins(username: str) -> None:
    with failed_login_lock:
        failed_login_attempts.pop(username, None)




def _prune_attempts(store: dict[str, list[datetime]], username: str, now: datetime) -> list[datetime]:
    window = timedelta(minutes=settings_conf.auth_lockout_minutes)
    attempts = store.get(username, [])
    pruned = [attempt for attempt in attempts if now - attempt < window]
    if pruned:
        store[username] = pruned
    else:
        store.pop(username, None)
    return pruned


def _is_mfa_verify_locked_out(username: str, now: datetime) -> bool:
    with failed_mfa_verify_lock:
        attempts = _prune_attempts(failed_mfa_verify_attempts, username, now)
        return len(attempts) >= settings_conf.auth_lockout_threshold


def _record_failed_mfa_verify(username: str, now: datetime) -> None:
    with failed_mfa_verify_lock:
        attempts = _prune_attempts(failed_mfa_verify_attempts, username, now)
        attempts.append(now)
        failed_mfa_verify_attempts[username] = attempts


def _clear_failed_mfa_verify(username: str) -> None:
    with failed_mfa_verify_lock:
        failed_mfa_verify_attempts.pop(username, None)


def _is_mfa_setup_locked_out(username: str, now: datetime) -> bool:
    with failed_mfa_setup_lock:
        attempts = _prune_attempts(failed_mfa_setup_attempts, username, now)
        return len(attempts) >= settings_conf.auth_lockout_threshold


def _record_failed_mfa_setup(username: str, now: datetime) -> None:
    with failed_mfa_setup_lock:
        attempts = _prune_attempts(failed_mfa_setup_attempts, username, now)
        attempts.append(now)
        failed_mfa_setup_attempts[username] = attempts


def _clear_failed_mfa_setup(username: str) -> None:
    with failed_mfa_setup_lock:
        failed_mfa_setup_attempts.pop(username, None)

def _write_auth_audit(
    sec_repo: SecurityRepository,
    *,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    ip_address: str | None,
    before_state: str | None = None,
    after_state: str | None = None,
) -> None:
    sec_repo.add_audit_log(
        actor_type="user",
        actor_id=actor_id,
        organization_id=None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
    )


@router.post("/token")
@router.post("/auth/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    username = form_data.username.strip()
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None

    if _is_locked_out(username, now):
        sec_repo.add_security_event(
            actor=username,
            event_type="login_locked",
            detail="Account temporarily locked",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=429, detail="Account temporarily locked")

    user = db.query(User).filter(User.username == username).first()
    if user and user.locked_until and _utc_normalized(user.locked_until) > now:
        sec_repo.add_security_event(
            actor=username,
            event_type="login_locked",
            detail="Account locked in persistent store",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=429, detail="Account temporarily locked")

    if user and not user.is_active:
        sec_repo.add_security_event(
            actor=username,
            event_type="login_inactive",
            detail="Inactive account",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=403, detail="Account inactive")

    if not user or not verify_password(form_data.password, user.password_hash):
        _record_failed_login(username, now)
        if user:
            user.failed_login_count = int(user.failed_login_count or 0) + 1
            user.last_failed_login_at = now
            if user.failed_login_count >= settings_conf.auth_lockout_threshold:
                user.locked_until = now + timedelta(minutes=settings_conf.auth_lockout_minutes)
                user.failed_login_count = 0
            db.commit()
        sec_repo.add_security_event(
            actor=username,
            event_type="login_failed",
            detail="Invalid credentials",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_failed_logins(username)
    user.failed_login_count = 0
    user.last_failed_login_at = None
    user.locked_until = None
    db.commit()

    if _require_mfa_for_user(user):
        if not user.mfa_enabled or not user.mfa_secret:
            sec_repo.add_security_event(
                actor=username,
                event_type="mfa_required_setup",
                detail="Admin login blocked until MFA setup",
                ip_address=client_ip,
            )
            raise HTTPException(status_code=403, detail="MFA setup required for admin account")
        return {
            "mfa_required": True,
            "mfa_token": create_mfa_token(subject=user.username),
            "token_type": "Bearer",
        }

    token = create_access_token(subject=user.username, role=user.role)
    refresh_token, jti = create_refresh_token(subject=user.username)
    refresh_exp = now + timedelta(minutes=settings_conf.refresh_token_expire_minutes)
    sec_repo.create_refresh_token(user.username, hash_token(jti), refresh_exp)
    sec_repo.add_security_event(
        actor=username,
        event_type="login_success",
        detail="Access and refresh token issued",
        ip_address=client_ip,
    )
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@router.post("/token/refresh")
@router.post("/auth/refresh")
@limiter.limit("20/minute")
def refresh_token(
    payload: RefreshPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    try:
        subject, jti = parse_refresh_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        sec_repo.add_security_event(
            actor="unknown",
            event_type="token_refresh_failed",
            detail="Malformed refresh token",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    token_record = sec_repo.get_active_refresh_token(hash_token(jti))
    if not token_record or _utc_normalized(token_record.expires_at) < datetime.now(
        timezone.utc
    ):
        sec_repo.add_security_event(
            actor=subject,
            event_type="token_refresh_failed",
            detail="Refresh token expired or revoked",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    user = db.query(User).filter(User.username == subject).first()
    if not user:
        sec_repo.add_security_event(
            actor=subject,
            event_type="token_refresh_failed",
            detail="Unknown user",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Unknown user")

    sec_repo.revoke_refresh_token(hash_token(jti))
    new_refresh, new_jti = create_refresh_token(subject=user.username)
    new_expiry = datetime.now(timezone.utc) + timedelta(
        minutes=settings_conf.refresh_token_expire_minutes
    )
    sec_repo.create_refresh_token(user.username, hash_token(new_jti), new_expiry)
    sec_repo.add_security_event(
        actor=user.username,
        event_type="token_refresh",
        detail="Refresh token rotated",
        ip_address=client_ip,
    )
    return {
        "access_token": create_access_token(subject=user.username, role=user.role),
        "refresh_token": new_refresh,
        "token_type": "Bearer",
    }


@router.post("/auth/logout")
def logout(
    payload: LogoutPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    try:
        subject, jti = parse_refresh_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    sec_repo.revoke_refresh_token(hash_token(jti))
    sec_repo.add_security_event(
        actor=subject,
        event_type="logout",
        detail="Refresh token revoked",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=subject,
        action="auth.logout",
        resource_type="refresh_token",
        resource_id=hash_token(jti),
        ip_address=client_ip,
    )
    return {"status": "logged_out"}


@router.post("/auth/logout-all")
def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    sec_repo = SecurityRepository(db)
    revoked = sec_repo.revoke_all_refresh_tokens_for_user(user.username)
    client_ip = request.client.host if request.client else None
    sec_repo.add_security_event(
        actor=user.username,
        event_type="logout_all",
        detail=f"revoked_tokens={revoked}",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=user.username,
        action="auth.logout_all",
        resource_type="refresh_token",
        resource_id=user.username,
        ip_address=client_ip,
        after_state=str(revoked),
    )
    return {"status": "logged_out_all", "revoked_tokens": revoked}


@router.post("/auth/password-reset/request")
@limiter.limit("5/minute")
def request_password_reset(
    payload: PasswordResetRequestPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    username = payload.username.strip()
    user = db.query(User).filter(User.username == username).first()

    if not user:
        sec_repo.add_security_event(
            actor=username,
            event_type="password_reset_request_unknown_user",
            detail="No matching account",
            ip_address=client_ip,
        )
        return {"status": "accepted"}

    raw_token = uuid4().hex + uuid4().hex
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    sec_repo.create_password_reset_token(
        username=username,
        token_hash=hash_token(raw_token),
        expires_at=expiry,
    )
    sec_repo.add_security_event(
        actor=username,
        event_type="password_reset_requested",
        detail="Password reset token issued",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=username,
        action="auth.password_reset.request",
        resource_type="password_reset_token",
        resource_id=username,
        ip_address=client_ip,
    )
    response = {"status": "accepted"}
    if settings_conf.environment == "dev":
        response["reset_token"] = raw_token
    return response


@router.post("/auth/password-reset/confirm")
@limiter.limit("10/minute")
def confirm_password_reset(
    payload: PasswordResetConfirmPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    token_hash = hash_token(payload.reset_token)
    record = sec_repo.get_active_password_reset_token(token_hash)
    now = datetime.now(timezone.utc)

    if not record or _utc_normalized(record.expires_at) < now:
        sec_repo.add_security_event(
            actor="unknown",
            event_type="password_reset_failed",
            detail="Reset token invalid or expired",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=400, detail="Reset token invalid or expired")

    try:
        validate_password_policy(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.query(User).filter(User.username == record.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(payload.new_password)
    user.password_changed_at = now
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    sec_repo.mark_password_reset_token_used(token_hash, now)
    sec_repo.revoke_all_refresh_tokens_for_user(user.username)
    sec_repo.add_security_event(
        actor=user.username,
        event_type="password_reset_success",
        detail="Password updated and sessions revoked",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=user.username,
        action="auth.password_reset.confirm",
        resource_type="user",
        resource_id=user.username,
        ip_address=client_ip,
    )
    return {"status": "password_updated"}


@router.post("/auth/activate", dependencies=[Depends(require_role("admin"))])
def activate_user(
    payload: ActivateUserPayload,
    request: Request,
    db: Session = Depends(get_db),
    actor: AuthUser = Depends(get_current_user),
):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = payload.active
    db.commit()
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    sec_repo.add_security_event(
        actor=actor.username,
        event_type="user_activation_changed",
        detail=f"target={user.username},active={payload.active}",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=actor.username,
        action="auth.activate",
        resource_type="user",
        resource_id=user.username,
        ip_address=client_ip,
        after_state=str(payload.active),
    )
    return {"username": user.username, "active": user.is_active}




@router.post("/auth/mfa/setup", dependencies=[Depends(require_role("admin"))])
@limiter.limit("30/minute")
def mfa_setup(
    payload: MFASetupPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    sec_repo = SecurityRepository(db)
    entity = db.query(User).filter(User.username == user.username).first()
    if not entity:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.regenerate or not entity.mfa_secret:
        secret = generate_totp_secret()
        recovery_codes = generate_recovery_codes()
        entity.mfa_secret = secret
        entity.mfa_enabled = False
        entity.mfa_recovery_codes = json.dumps(_hash_recovery_codes(recovery_codes), sort_keys=True)
        db.commit()
    else:
        secret = entity.mfa_secret
        recovery_codes = []

    client_ip = request.client.host if request.client else None

    if payload.code:
        now = datetime.now(timezone.utc)
        if _is_mfa_setup_locked_out(user.username, now):
            sec_repo.add_security_event(
                actor=user.username,
                event_type="mfa_enable_locked",
                detail="Too many invalid MFA setup attempts",
                ip_address=client_ip,
            )
            _write_auth_audit(
                sec_repo,
                actor_id=user.username,
                action="auth.mfa.enable.locked",
                resource_type="user",
                resource_id=user.username,
                ip_address=client_ip,
            )
            raise HTTPException(status_code=429, detail="MFA setup temporarily locked")

        if not verify_totp_code(secret, payload.code):
            _record_failed_mfa_setup(user.username, now)
            sec_repo.add_security_event(
                actor=user.username,
                event_type="mfa_enable_failed",
                detail="Invalid MFA setup code",
                ip_address=client_ip,
            )
            _write_auth_audit(
                sec_repo,
                actor_id=user.username,
                action="auth.mfa.enable.failed",
                resource_type="user",
                resource_id=user.username,
                ip_address=client_ip,
            )
            raise HTTPException(status_code=401, detail="Invalid MFA code")
        _clear_failed_mfa_setup(user.username)
        entity.mfa_enabled = True
        db.commit()
        sec_repo.add_security_event(
            actor=user.username,
            event_type="mfa_enabled",
            detail="Admin MFA enabled",
            ip_address=client_ip,
        )
        _write_auth_audit(
            sec_repo,
            actor_id=user.username,
            action="auth.mfa.enable",
            resource_type="user",
            resource_id=user.username,
            ip_address=client_ip,
            after_state="enabled",
        )
        return {"status": "mfa_enabled"}

    sec_repo.add_security_event(
        actor=user.username,
        event_type="mfa_setup_initiated",
        detail="MFA secret provisioned",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=user.username,
        action="auth.mfa.setup",
        resource_type="user",
        resource_id=user.username,
        ip_address=client_ip,
        after_state="setup_ready",
    )

    return {
        "status": "setup_ready",
        "secret": secret,
        "totp_uri": f"otpauth://totp/Recall:{user.username}?secret={secret}&issuer=Recall",
        "recovery_codes": recovery_codes,
    }


@router.post("/auth/mfa/verify")
@limiter.limit("10/minute")
def mfa_verify(
    payload: MFAVerifyPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None

    if not payload.mfa_token:
        raise HTTPException(status_code=400, detail="mfa_token is required")
    if payload.code and payload.recovery_code:
        raise HTTPException(status_code=400, detail="Provide either code or recovery_code")
    if not payload.code and not payload.recovery_code:
        raise HTTPException(status_code=400, detail="Either code or recovery_code is required")

    try:
        username = parse_mfa_token(payload.mfa_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid MFA token") from exc
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.mfa_secret or not user.mfa_enabled:
        raise HTTPException(status_code=403, detail="MFA not configured")

    now = datetime.now(timezone.utc)
    if _is_mfa_verify_locked_out(username, now):
        sec_repo.add_security_event(
            actor=username,
            event_type="mfa_locked",
            detail="Too many invalid MFA attempts",
            ip_address=client_ip,
        )
        _write_auth_audit(
            sec_repo,
            actor_id=username,
            action="auth.mfa.verify.locked",
            resource_type="user",
            resource_id=username,
            ip_address=client_ip,
        )
        raise HTTPException(status_code=429, detail="MFA temporarily locked")

    valid = verify_totp_code(user.mfa_secret, payload.code or "") or _verify_recovery_code(user, payload.recovery_code)
    if not valid:
        _record_failed_mfa_verify(username, now)
        sec_repo.add_security_event(
            actor=username,
            event_type="mfa_verify_failed",
            detail="Invalid MFA code",
            ip_address=client_ip,
        )
        _write_auth_audit(
            sec_repo,
            actor_id=username,
            action="auth.mfa.verify.failed",
            resource_type="user",
            resource_id=username,
            ip_address=client_ip,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    _clear_failed_mfa_verify(username)
    access = create_access_token(subject=user.username, role=user.role)
    refresh, jti = create_refresh_token(subject=user.username)
    refresh_exp = datetime.now(timezone.utc) + timedelta(minutes=settings_conf.refresh_token_expire_minutes)
    sec_repo.create_refresh_token(user.username, hash_token(jti), refresh_exp)
    sec_repo.add_security_event(
        actor=username,
        event_type="mfa_verify_success",
        detail="MFA challenge completed",
        ip_address=client_ip,
    )
    _write_auth_audit(
        sec_repo,
        actor_id=username,
        action="auth.mfa.verify",
        resource_type="user",
        resource_id=username,
        ip_address=client_ip,
    )
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.get("/audit-logs", dependencies=[Depends(require_role("admin"))])
def audit_logs(
    limit: int = 100,
    actor: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    rows = SecurityRepository(db).list_security_events(
        limit=max(1, min(limit, 500)), actor=actor, event_type=event_type
    )
    return [
        {
            "id": row.id,
            "actor": row.actor,
            "event_type": row.event_type,
            "detail": row.detail,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]
