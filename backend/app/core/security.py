from datetime import datetime, timedelta, timezone
import hashlib
import re
import socket
import uuid

from jose import jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)




def validate_password_policy(password: str) -> None:
    failures: list[str] = []
    if len(password) < settings.password_min_length:
        failures.append(f"minimum length is {settings.password_min_length}")
    if settings.password_require_upper and not re.search(r"[A-Z]", password):
        failures.append("at least one uppercase letter required")
    if settings.password_require_lower and not re.search(r"[a-z]", password):
        failures.append("at least one lowercase letter required")
    if settings.password_require_digit and not re.search(r"[0-9]", password):
        failures.append("at least one digit required")
    if settings.password_require_symbol and not re.search(r"[^A-Za-z0-9]", password):
        failures.append("at least one symbol required")
    if failures:
        raise ValueError("Password policy failed: " + "; ".join(failures))


def create_access_token(
    subject: str, role: str, expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str, expires_delta: timedelta | None = None
) -> tuple[str, str]:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes)
    )
    jti = uuid.uuid4().hex
    payload = {"sub": subject, "exp": expire, "type": "refresh", "jti": jti}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def parse_refresh_token(token: str) -> tuple[str, str]:
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")
    subject = payload.get("sub")
    jti = payload.get("jti")
    if not subject or not jti:
        raise ValueError("Malformed refresh token")
    return str(subject), str(jti)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clamav_scan(
    file_bytes: bytes,
    host: str = "localhost",
    port: int = 3310,
    fail_open: bool = False,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1) as sock:
            sock.sendall(b"zINSTREAM\0")
            chunk = len(file_bytes).to_bytes(4, "big") + file_bytes
            sock.sendall(chunk)
            sock.sendall((0).to_bytes(4, "big"))
            response = sock.recv(256).decode("utf-8", errors="ignore")
            return "OK" in response
    except OSError:
        return fail_open
