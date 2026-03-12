from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.models.settings import User

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "superadmin": {
        "users.read",
        "users.write",
        "devices.read",
        "devices.write",
        "devices.manage",
        "media.read",
        "media.upload",
        "media.delete",
        "playlists.read",
        "playlists.manage",
        "settings.read",
        "settings.manage",
        "system.reboot",
        "system.update",
        "monitor.read",
        "monitor.write",
    },
    "admin": {
        "users.read",
        "users.write",
        "devices.read",
        "devices.write",
        "devices.manage",
        "media.read",
        "media.upload",
        "media.delete",
        "playlists.read",
        "playlists.manage",
        "settings.read",
        "settings.manage",
        "system.reboot",
        "system.update",
        "monitor.read",
        "monitor.write",
    },
    "operator": {
        "devices.read",
        "devices.write",
        "media.read",
        "media.upload",
        "playlists.read",
        "playlists.manage",
        "settings.read",
        "monitor.read",
        "monitor.write",
    },
    "editor": {
        "media.read",
        "media.upload",
    },
    "reviewer": {
        "media.read",
        "media.upload",
        "playlists.read",
    },
    "viewer": {
        "devices.read",
        "media.read",
        "playlists.read",
        "settings.read",
        "monitor.read",
    },
    "device": {
        "devices.write",
        "monitor.write",
    },
}


class AuthUser(BaseModel):
    username: str
    role: str
    organization_id: int | None = None


def normalize_permission(permission: str) -> str:
    perm = permission.strip().lower().replace(":", ".")
    aliases = {
        "media.write": "media.upload",
        "playlists.write": "playlists.manage",
        "settings.write": "settings.manage",
        "system.write": "system.update",
    }
    if perm.endswith(".manage"):
        return perm
    return aliases.get(perm, perm)


def role_has_permission(role: str, permission: str) -> bool:
    normalized = normalize_permission(permission)
    normalized_perms = {
        normalize_permission(p) for p in ROLE_PERMISSIONS.get(role, set())
    }

    if normalized in normalized_perms:
        return True

    # manage supersets for common domains
    if normalized.endswith(".write"):
        manage = normalized.replace(".write", ".manage")
        if manage in normalized_perms:
            return True

    return False


def enforce_role_permission(role: str, permission: str) -> None:
    if not role_has_permission(role, permission):
        raise PermissionError(f"missing permission: {permission}")


def ensure_organization_access(user: AuthUser, organization_id: int | None) -> None:
    if user.role in {"admin", "superadmin"} and user.organization_id is None:
        return
    if user.organization_id is None:
        raise HTTPException(status_code=403, detail="Organization context required")
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
