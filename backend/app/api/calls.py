"""Call ingestion + dashboard read endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, desc, select

from app.core.auth import require_api_key
from app.core.db import get_session
from app.models.call import Call
from app.services.happyrobot_translate import translate

router = APIRouter(tags=["calls"])


Outcome = Literal[
    "booked",
    "declined",
    "no_match",
    "ineligible_carrier",
    "negotiation_failed",
    "transferred",
    "other",
]
Sentiment = Literal["positive", "neutral", "negative"]


class IngestCallRequest(BaseModel):
    mc_number: str | None = None
    carrier_name: str | None = None
    eligible: bool | None = None
    load_id: str | None = None
    outcome: Outcome
    sentiment: Sentiment
    rounds: int = Field(0, ge=0)
    loadboard_rate: float | None = None
    final_carrier_offer: float | None = None
    agreed_price: float | None = None
    transcript: str | None = None
    notes: str | None = None
    raw: dict | None = None


class CallDTO(BaseModel):
    id: int
    created_at: datetime
    mc_number: str | None
    carrier_name: str | None
    eligible: bool | None
    load_id: str | None
    outcome: str
    sentiment: str
    rounds: int
    loadboard_rate: float | None
    final_carrier_offer: float | None
    agreed_price: float | None
    transcript: str | None
    notes: str | None


@router.post(
    "/calls",
    response_model=CallDTO,
    dependencies=[Depends(require_api_key)],
    summary="Ingest an end-of-call payload from the HappyRobot agent",
)
def ingest_call(
    payload: IngestCallRequest,
    session: Session = Depends(get_session),
) -> CallDTO:
    call = Call(
        mc_number=payload.mc_number,
        carrier_name=payload.carrier_name,
        eligible=payload.eligible,
        load_id=payload.load_id,
        outcome=payload.outcome,
        sentiment=payload.sentiment,
        rounds=payload.rounds,
        loadboard_rate=payload.loadboard_rate,
        final_carrier_offer=payload.final_carrier_offer,
        agreed_price=payload.agreed_price,
        transcript=payload.transcript,
        notes=payload.notes,
        raw=json.dumps(payload.raw) if payload.raw is not None else None,
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    return CallDTO.model_validate(call.model_dump())


class ListCallsResponse(BaseModel):
    count: int
    calls: list[CallDTO]


@router.post(
    "/calls/happyrobot",
    response_model=CallDTO,
    dependencies=[Depends(require_api_key)],
    summary="Ingest a HappyRobot end-of-call payload (Classify + Extract).",
)
def ingest_happyrobot_call(
    payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> CallDTO:
    try:
        canonical = translate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    call = Call(
        mc_number=canonical.mc_number,
        carrier_name=canonical.carrier_name,
        eligible=canonical.eligible,
        load_id=canonical.load_id,
        outcome=canonical.outcome,
        sentiment=canonical.sentiment,
        rounds=canonical.rounds,
        loadboard_rate=canonical.loadboard_rate,
        final_carrier_offer=canonical.final_carrier_offer,
        agreed_price=canonical.agreed_price,
        transcript=canonical.transcript,
        notes=canonical.notes,
        raw=json.dumps(canonical.raw),
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    return CallDTO.model_validate(call.model_dump())


@router.get(
    "/calls",
    response_model=ListCallsResponse,
    dependencies=[Depends(require_api_key)],
    summary="List recent calls (newest first)",
)
def list_calls(
    session: Session = Depends(get_session),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    outcome: str | None = None,
    sentiment: str | None = None,
) -> ListCallsResponse:
    stmt = select(Call).order_by(desc(Call.created_at))
    if outcome:
        stmt = stmt.where(Call.outcome == outcome)
    if sentiment:
        stmt = stmt.where(Call.sentiment == sentiment)
    stmt = stmt.offset(offset).limit(limit)
    rows = list(session.exec(stmt).all())
    return ListCallsResponse(
        count=len(rows),
        calls=[CallDTO.model_validate(r.model_dump()) for r in rows],
    )
