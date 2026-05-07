"""Carrier verification endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.auth import require_api_key
from app.core.limiter import limiter
from app.core.settings import get_settings
from app.services.fmcsa import FMCSAClient

router = APIRouter(tags=["verify"])
_client = FMCSAClient()
_settings = get_settings()


class VerifyRequest(BaseModel):
    mc_number: str = Field(..., min_length=1, description="Motor Carrier (MC) number")


class VerifyResponse(BaseModel):
    eligible: bool
    mc_number: str
    carrier_name: str | None
    dot_number: str | None
    allowed_to_operate: str | None
    operating_status: str | None
    reasons: list[str]


@router.post(
    "/verify_carrier",
    response_model=VerifyResponse,
    dependencies=[Depends(require_api_key)],
    summary="Verify a carrier via FMCSA",
)
@limiter.limit(_settings.rate_limit_verify)
async def verify_carrier(request: Request, payload: VerifyRequest) -> VerifyResponse:
    result = await _client.verify(payload.mc_number)
    return VerifyResponse(
        eligible=result.eligible,
        mc_number=result.mc_number,
        carrier_name=result.carrier_name,
        dot_number=result.dot_number,
        allowed_to_operate=result.allowed_to_operate,
        operating_status=result.operating_status,
        reasons=result.reasons,
    )
