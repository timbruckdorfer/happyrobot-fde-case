"""Call event record produced at end-of-call by the HappyRobot agent."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Call(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )

    mc_number: str | None = Field(default=None, index=True)
    carrier_name: str | None = None
    eligible: bool | None = None

    load_id: str | None = Field(default=None, index=True)

    outcome: str = Field(index=True)
    sentiment: str = Field(index=True)

    rounds: int = 0
    loadboard_rate: float | None = None
    final_carrier_offer: float | None = None
    agreed_price: float | None = None

    transcript: str | None = None
    notes: str | None = None
    raw: str | None = None
