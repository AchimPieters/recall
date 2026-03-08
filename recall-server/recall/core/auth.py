from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from recall.core.config import get_settings
from recall.db.database import get_db
from recall.models.settings import User

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
        permissions = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in permissions:
            raise HTTPException(status_code=403, detail="Missing permission")
        return user

    return checker
