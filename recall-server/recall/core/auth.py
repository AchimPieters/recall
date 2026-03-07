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


class AuthUser(BaseModel):
    username: str
    role: str


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AuthUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")
        role: str = payload.get("role", "viewer")
        if username is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    return AuthUser(username=user.username, role=role)


def require_role(*roles: str):
    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker
