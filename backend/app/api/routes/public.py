from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from backend.app.core.public_api_auth import PublicApiContext, get_public_api_context

router = APIRouter(tags=["public-api"])


class PublicPingResponse(BaseModel):
    status: str
    tenant: str
    version: str


@router.get("/health", response_model=PublicPingResponse)
def public_health(
    response: Response,
    context: PublicApiContext = Depends(get_public_api_context),
) -> PublicPingResponse:
    response.headers["X-RateLimit-Limit"] = str(context.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(context.rate_limit_remaining)
    response.headers["X-RateLimit-Reset"] = str(context.rate_limit_reset_seconds)
    response.headers["X-Public-Tenant"] = context.tenant
    return PublicPingResponse(status="ok", tenant=context.tenant, version="v1")
