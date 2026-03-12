from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import Depends, Header, HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import hash_token
from backend.app.db.database import get_db
from backend.app.models import PublicApiKey


@dataclass(frozen=True)
class PublicApiClient:
    tenant: str
    rate_limit_per_minute: int


@dataclass(frozen=True)
class PublicApiContext:
    tenant: str
    api_key_id: str


_rate_limit_store: dict[str, list[datetime]] = {}
_rate_limit_lock = Lock()


def _parse_public_api_keys(raw: str) -> dict[str, PublicApiClient]:
    clients: dict[str, PublicApiClient] = {}
    for entry in raw.split(","):
        item = entry.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 3:
            continue
        api_key, tenant, rate_str = parts
        if not api_key or not tenant:
            continue
        try:
            rate = int(rate_str)
        except ValueError:
            continue
        if rate < 1:
            continue
        clients[api_key] = PublicApiClient(tenant=tenant, rate_limit_per_minute=rate)
    return clients


def _prune_entries(cache_key: str, now: datetime) -> list[datetime]:
    window = timedelta(minutes=1)
    attempts = _rate_limit_store.get(cache_key, [])
    pruned = [attempt for attempt in attempts if now - attempt < window]
    if pruned:
        _rate_limit_store[cache_key] = pruned
    else:
        _rate_limit_store.pop(cache_key, None)
    return pruned


def _enforce_tenant_rate_limit(*, tenant: str, limit: int, now: datetime) -> None:
    cache_key = f"tenant:{tenant}"
    with _rate_limit_lock:
        attempts = _prune_entries(cache_key, now)
        if len(attempts) >= limit:
            raise HTTPException(status_code=429, detail="Public API tenant rate limit exceeded")
        attempts.append(now)
        _rate_limit_store[cache_key] = attempts


def get_public_api_context(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> PublicApiContext:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    hashed = hash_token(x_api_key)
    try:
        row = db.query(PublicApiKey).filter(PublicApiKey.key_hash == hashed, PublicApiKey.is_active == True).first()  # noqa: E712
    except OperationalError:
        row = None

    if row is None:
        settings = get_settings()
        clients = _parse_public_api_keys(settings.public_api_keys)
        client = clients.get(x_api_key)
        if client is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        now = datetime.now(timezone.utc)
        _enforce_tenant_rate_limit(tenant=client.tenant, limit=client.rate_limit_per_minute, now=now)
        return PublicApiContext(tenant=client.tenant, api_key_id=x_api_key[:6])

    now = datetime.now(timezone.utc)
    tenant = "global" if row.organization_id is None else f"org-{row.organization_id}"
    _enforce_tenant_rate_limit(tenant=tenant, limit=row.rate_limit_per_minute, now=now)
    return PublicApiContext(tenant=tenant, api_key_id=str(row.id))


def reset_public_api_rate_limits_for_tests() -> None:
    with _rate_limit_lock:
        _rate_limit_store.clear()
