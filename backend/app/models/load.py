"""Load record (matches the schema in the take-home brief)."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Load(SQLModel, table=True):
    load_id: str = Field(primary_key=True, index=True)
    origin: str = Field(index=True)
    destination: str = Field(index=True)
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str = Field(index=True)
    loadboard_rate: float
    notes: str | None = None
    weight: float
    commodity_type: str
    num_of_pieces: int
    miles: float
    dimensions: str
