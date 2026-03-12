from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from datetime import datetime, timezone


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8").rstrip("=")


def _normalize_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding)


def generate_totp_code(
    secret: str, for_time: datetime | None = None, interval_seconds: int = 30
) -> str:
    now = for_time or datetime.now(timezone.utc)
    counter = int(now.timestamp() // interval_seconds)
    key = _normalize_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (
        struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    ) % 1_000_000
    return f"{code_int:06d}"


def verify_totp_code(
    secret: str, code: str, allowed_drift_steps: int = 1, interval_seconds: int = 30
) -> bool:
    code = (code or "").strip()
    if len(code) != 6 or not code.isdigit():
        return False

    now = datetime.now(timezone.utc)
    base_counter = int(now.timestamp() // interval_seconds)
    key = _normalize_secret(secret)
    for drift in range(-allowed_drift_steps, allowed_drift_steps + 1):
        msg = struct.pack(">Q", base_counter + drift)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = (
            struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        ) % 1_000_000
        if hmac.compare_digest(f"{code_int:06d}", code):
            return True
    return False


def generate_recovery_codes(count: int = 8) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        raw = os.urandom(6).hex()
        codes.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}")
    return codes
