"""Load search and detail endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.auth import require_api_key
from app.core.db import get_session
from app.models.load import Load
from app.services.loadsearch import search_loads

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
    load = session.get(Load, load_id)
    if not load:
        raise HTTPException(status_code=404, detail=f"Load {load_id} not found")
    return LoadDTO.from_model(load)
