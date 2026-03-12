from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.public_api_auth import PublicApiContext, get_public_api_context

router = APIRouter(tags=["public-api"])


class PublicPingResponse(BaseModel):
    status: str
    tenant: str
    version: str


@router.get("/health", response_model=PublicPingResponse)
def public_health(context: PublicApiContext = Depends(get_public_api_context)) -> PublicPingResponse:
    return PublicPingResponse(status="ok", tenant=context.tenant, version="v1")
