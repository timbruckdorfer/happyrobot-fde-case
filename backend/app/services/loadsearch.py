"""Load search & ranking."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.load import Load


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _location_match_score(query: str, value: str) -> float:
    q, v = _norm(query), _norm(value)
    if not q:
        return 0.0
    if q == v:
        return 1.0
    if q in v or v in q:
        return 0.7
    q_tokens = {t for t in q.replace(",", " ").split() if t}
    v_tokens = {t for t in v.replace(",", " ").split() if t}
    overlap = q_tokens & v_tokens
    if not q_tokens:
        return 0.0
    return 0.5 * len(overlap) / len(q_tokens)


def search_loads(
    session: Session,
    *,
    equipment_type: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    pickup_after: datetime | None = None,
    max_results: int = 5,
) -> list[Load]:
    stmt = select(Load)
    if equipment_type:
        stmt = stmt.where(Load.equipment_type.ilike(f"%{equipment_type.strip()}%"))
    if pickup_after:
        stmt = stmt.where(Load.pickup_datetime >= pickup_after)
    candidates = list(session.exec(stmt).all())

    now = datetime.now(UTC).replace(tzinfo=None)

    def score(load: Load) -> float:
        s = 0.0
        if origin:
            s += 2.0 * _location_match_score(origin, load.origin)
        if destination:
            s += 2.0 * _location_match_score(destination, load.destination)
        delta_hours = abs((load.pickup_datetime - now).total_seconds()) / 3600.0
        s += max(0.0, 1.0 - delta_hours / 240.0)
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[:max_results]
