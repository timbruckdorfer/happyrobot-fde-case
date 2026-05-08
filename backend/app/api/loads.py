"""Load search and detail endpoints."""

from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from app.core.auth import require_api_key
from app.core.db import get_session
from app.models.load import Load
from app.services.loadsearch import search_loads


def normalize_load_id(s: str) -> str:
    """Reduce a user-supplied load reference to its canonical form.

    Voice agents pass identifiers as the transcriber produced them, which
    means a single carrier saying "REF one zero zero one" can arrive as
    "REF1001", "ref1001", "REF 1001", "ref 1001", or even "R E F 1 0 0 1".
    We strip everything that isn't a letter or digit and uppercase the rest,
    so all of those resolve to "REF1001" — the canonical form stored in DB.
    """
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

router = APIRouter(tags=["loads"])


class SearchRequest(BaseModel):
    equipment_type: str | None = None
    origin: str | None = None
    destination: str | None = None
    pickup_after: datetime | None = None
    max_results: int = Field(5, ge=1, le=25)


class LoadDTO(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: str | None
    weight: float
    commodity_type: str
    num_of_pieces: int
    miles: float
    dimensions: str

    @classmethod
    def from_model(cls, m: Load) -> LoadDTO:
        return cls(**m.model_dump())


class SearchResponse(BaseModel):
    count: int
    loads: list[LoadDTO]


@router.post(
    "/search_loads",
    response_model=SearchResponse,
    dependencies=[Depends(require_api_key)],
    summary="Search loads matching carrier preferences",
)
def search_loads_endpoint(
    payload: SearchRequest,
    session: Session = Depends(get_session),
) -> SearchResponse:
    results = search_loads(
        session,
        equipment_type=payload.equipment_type,
        origin=payload.origin,
        destination=payload.destination,
        pickup_after=payload.pickup_after,
        max_results=payload.max_results,
    )
    return SearchResponse(count=len(results), loads=[LoadDTO.from_model(r) for r in results])


@router.get(
    "/loads/{load_id}",
    response_model=LoadDTO,
    dependencies=[Depends(require_api_key)],
    summary="Get a single load by ID",
)
def get_load(load_id: str, session: Session = Depends(get_session)) -> LoadDTO:
    # Normalize the input — see normalize_load_id() for why.
    canonical = normalize_load_id(load_id)
    load = session.exec(
        select(Load).where(func.upper(Load.load_id) == canonical)
    ).first()
    if not load:
        raise HTTPException(status_code=404, detail=f"Load {load_id} not found")
    return LoadDTO.from_model(load)
