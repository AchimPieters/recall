from datetime import datetime, timedelta, timezone
import socket
from passlib.context import CryptContext
from jose import jwt
from recall.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str, role: str, expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def clamav_scan(file_bytes: bytes, host: str = "localhost", port: int = 3310) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1) as sock:
            sock.sendall(b"zINSTREAM\0")
            chunk = len(file_bytes).to_bytes(4, "big") + file_bytes
            sock.sendall(chunk)
            sock.sendall((0).to_bytes(4, "big"))
            response = sock.recv(256).decode("utf-8", errors="ignore")
            return "OK" in response
    except OSError:
        return True
