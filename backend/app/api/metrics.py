"""Aggregated metrics endpoint for the dashboard."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import require_api_key
from app.core.db import get_session
from app.models.call import Call

router = APIRouter(tags=["metrics"])


SENTIMENT_VALUES = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


class TimeseriesPoint(BaseModel):
    date: str
    calls: int
    booked: int
    conversion_rate: float


class DistributionItem(BaseModel):
    label: str
    count: int


class MetricsResponse(BaseModel):
    total_calls: int
    booked_calls: int
    conversion_rate: float
    avg_rounds: float
    avg_margin_delta: float
    avg_margin_pct: float
    avg_sentiment_score: float
    eligible_rate: float
    outcomes: list[DistributionItem]
    sentiments: list[DistributionItem]
    equipment_types: list[DistributionItem]
    top_lanes: list[DistributionItem]
    timeseries: list[TimeseriesPoint]


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(require_api_key)],
    summary="Aggregated KPIs and distributions for the dashboard",
)
def metrics(
    session: Session = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
) -> MetricsResponse:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = list(session.exec(select(Call).where(Call.created_at >= since)).all())
    total = len(rows)

    booked = [c for c in rows if c.outcome == "booked"]
    conversion = (len(booked) / total) if total else 0.0
    avg_rounds = (sum(c.rounds for c in rows) / total) if total else 0.0

    margin_deltas = [
        (c.agreed_price - c.loadboard_rate)
        for c in rows
        if c.agreed_price is not None and c.loadboard_rate
    ]
    margin_pcts = [
        ((c.agreed_price - c.loadboard_rate) / c.loadboard_rate)
        for c in rows
        if c.agreed_price is not None and c.loadboard_rate
    ]
    avg_margin_delta = (sum(margin_deltas) / len(margin_deltas)) if margin_deltas else 0.0
    avg_margin_pct = (sum(margin_pcts) / len(margin_pcts)) if margin_pcts else 0.0

    sentiment_scores = [SENTIMENT_VALUES.get(c.sentiment, 0.0) for c in rows]
    avg_sentiment = (sum(sentiment_scores) / total) if total else 0.0

    eligible_known = [c for c in rows if c.eligible is not None]
    eligible_rate = (
        sum(1 for c in eligible_known if c.eligible) / len(eligible_known)
    ) if eligible_known else 0.0

    outcomes = Counter(c.outcome for c in rows)
    sentiments = Counter(c.sentiment for c in rows)

    load_ids = [c.load_id for c in rows if c.load_id]
    equipment_types: Counter[str] = Counter()
    top_lanes: Counter[str] = Counter()
    if load_ids:
        from app.models.load import Load
        load_map = {
            row.load_id: row
            for row in session.exec(select(Load).where(Load.load_id.in_(load_ids))).all()
        }
        for c in rows:
            if c.load_id and c.load_id in load_map:
                ld = load_map[c.load_id]
                equipment_types[ld.equipment_type] += 1
                top_lanes[f"{ld.origin} -> {ld.destination}"] += 1

    by_day: dict[str, dict[str, int]] = {}
    for c in rows:
        day = c.created_at.date().isoformat()
        by_day.setdefault(day, {"calls": 0, "booked": 0})
        by_day[day]["calls"] += 1
        if c.outcome == "booked":
            by_day[day]["booked"] += 1
    timeseries = [
        TimeseriesPoint(
            date=day,
            calls=stats["calls"],
            booked=stats["booked"],
            conversion_rate=(stats["booked"] / stats["calls"]) if stats["calls"] else 0.0,
        )
        for day, stats in sorted(by_day.items())
    ]

    return MetricsResponse(
        total_calls=total,
        booked_calls=len(booked),
        conversion_rate=conversion,
        avg_rounds=avg_rounds,
        avg_margin_delta=avg_margin_delta,
        avg_margin_pct=avg_margin_pct,
        avg_sentiment_score=avg_sentiment,
        eligible_rate=eligible_rate,
        outcomes=[DistributionItem(label=k, count=v) for k, v in outcomes.most_common()],
        sentiments=[DistributionItem(label=k, count=v) for k, v in sentiments.most_common()],
        equipment_types=[
            DistributionItem(label=k, count=v) for k, v in equipment_types.most_common()
        ],
        top_lanes=[DistributionItem(label=k, count=v) for k, v in top_lanes.most_common(5)],
        timeseries=timeseries,
    )
