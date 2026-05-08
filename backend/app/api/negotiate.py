"""Negotiation endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from app.api.loads import normalize_load_id
from app.core.auth import require_api_key
from app.core.db import get_session
from app.core.settings import Settings, get_settings
from app.models.load import Load
from app.services.negotiation import evaluate_offer

router = APIRouter(tags=["negotiation"])


class OfferRequest(BaseModel):
    load_id: str
    carrier_offer: float = Field(..., gt=0)
    round: int = Field(..., ge=1, description="1-indexed negotiation round")
    last_broker_price: float | None = Field(
        default=None,
        gt=0,
        description="Optional: previous broker price; defaults to loadboard_rate.",
    )


class OfferResponse(BaseModel):
    decision: Literal["accept", "counter", "reject"]
    counter_price: float | None
    rationale: str
    round: int
    final_round: int
    loadboard_rate: float
    floor: float
    ceiling: float


@router.post(
    "/evaluate_offer",
    response_model=OfferResponse,
    dependencies=[Depends(require_api_key)],
    summary="Evaluate a carrier's price offer",
)
def evaluate_offer_endpoint(
    payload: OfferRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OfferResponse:
    # Normalize for the same reasons GET /api/loads does — voice agents
    # produce arbitrary case/whitespace combinations.
    canonical = normalize_load_id(payload.load_id)
    load = session.exec(
        select(Load).where(func.upper(Load.load_id) == canonical)
    ).first()
    if not load:
        raise HTTPException(status_code=404, detail=f"Load {payload.load_id} not found")

    decision = evaluate_offer(
        loadboard_rate=load.loadboard_rate,
        carrier_offer=payload.carrier_offer,
        round_number=payload.round,
        floor_pct=settings.negotiation_floor_pct,
        ceiling_pct=settings.negotiation_ceiling_pct,
        max_rounds=settings.negotiation_max_rounds,
        last_broker_price=payload.last_broker_price,
    )
    return OfferResponse(
        decision=decision.decision,
        counter_price=decision.counter_price,
        rationale=decision.rationale,
        round=decision.round,
        final_round=decision.final_round,
        loadboard_rate=load.loadboard_rate,
        floor=round(load.loadboard_rate * settings.negotiation_floor_pct, 2),
        ceiling=round(load.loadboard_rate * settings.negotiation_ceiling_pct, 2),
    )
