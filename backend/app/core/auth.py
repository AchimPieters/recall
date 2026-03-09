from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.models.settings import User

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "devices:read",
        "devices:write",
        "media:read",
        "media:write",
        "playlists:read",
        "playlists:write",
        "settings:read",
        "settings:write",
        "system:write",
        "monitor:read",
        "monitor:write",
        "users:read",
        "users:write",
    },
    "operator": {
        "devices:read",
        "devices:write",
        "media:read",
        "media:write",
        "playlists:read",
        "playlists:write",
        "settings:read",
        "monitor:read",
        "monitor:write",
    },
    "viewer": {
        "devices:read",
        "media:read",
        "playlists:read",
        "settings:read",
        "monitor:read",
    },
    "device": {"devices:write", "monitor:write"},
}


class AuthUser(BaseModel):
    username: str
    role: str
    organization_id: int | None = None


def normalize_permission(permission: str) -> str:
    perm = permission.strip().lower().replace('.', ':')
    if perm.endswith(':manage'):
        return perm.replace(':manage', ':write')
    return perm


def role_has_permission(role: str, permission: str) -> bool:
    normalized = normalize_permission(permission)
    permissions = {normalize_permission(p) for p in ROLE_PERMISSIONS.get(role, set())}
    return normalized in permissions


def enforce_role_permission(role: str, permission: str) -> None:
    if not role_has_permission(role, permission):
        raise PermissionError(f"missing permission: {permission}")


def ensure_organization_access(user: AuthUser, organization_id: int | None) -> None:
    if user.role == "admin" and user.organization_id is None:
        return
    if user.organization_id is None:
        return
    if organization_id is None or organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AuthUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    secrets = settings.jwt_secrets or [settings.jwt_secret]
    payload: dict | None = None
    for secret in secrets:
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
            break
        except JWTError:
            continue

    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception

    return AuthUser(
        username=user.username,
        role=user.role,
        organization_id=user.organization_id,
    )


def require_role(*roles: str):
    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker


def require_permission(permission: str):
    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not role_has_permission(user.role, permission):
            raise HTTPException(status_code=403, detail="Missing permission")
        return user

    return checker
