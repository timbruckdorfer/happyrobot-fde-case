"""Translate HappyRobot end-of-call payloads into canonical Call records.

The HappyRobot inbound workflow's `Classify` node emits one of a small set of
human-readable tags, and the `Extract` node emits a flat object pulled from the
transcript. This module maps those into the strict canonical schema the dashboard
reads.

Keep the mapping explicit and reviewable so the dashboard's enums stay clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CANONICAL_OUTCOMES = {
    "booked",
    "declined",
    "no_match",
    "ineligible_carrier",
    "negotiation_failed",
    "transferred",
    "other",
}

CANONICAL_SENTIMENTS = {"positive", "neutral", "negative"}


CLASSIFICATION_TO_OUTCOME: dict[str, str] = {
    "success": "booked",
    "sucess": "booked",  # template typo
    "rate too high": "negotiation_failed",
    "not interested": "declined",
    "ineligible carrier": "ineligible_carrier",
    "no match": "no_match",
    "transferred": "transferred",
    "booked": "booked",
}


SENTIMENT_FALLBACK_BY_OUTCOME: dict[str, str] = {
    "booked": "positive",
    "transferred": "positive",
    "declined": "neutral",
    "no_match": "neutral",
    "ineligible_carrier": "neutral",
    "negotiation_failed": "negative",
    "other": "neutral",
}


@dataclass
class CanonicalCall:
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
    raw: dict[str, Any]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_bool(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"true", "yes", "y", "1"}:
        return True
    if s in {"false", "no", "n", "0"}:
        return False
    return None


def translate(payload: dict[str, Any]) -> CanonicalCall:
    """Translate a HappyRobot end-of-call payload into a canonical Call record.

    Recognised input fields (all optional unless noted):
      classification (REQUIRED) - Classify tag
      sentiment - explicit sentiment tag (else derived from outcome)
      reference_number - load id
      mc_number, carrier_name
      eligible - explicit verification result
      booking_decision - "yes"/"no"
      decline_reason - free text (e.g., "rate too high")
      rounds, loadboard_rate, final_carrier_offer, agreed_price
      transcript, call_duration, notes
    """
    classification_raw = payload.get("classification") or payload.get("outcome")
    if not classification_raw:
        raise ValueError("payload missing 'classification' (or 'outcome')")

    classification = _norm(classification_raw)
    outcome = CLASSIFICATION_TO_OUTCOME.get(classification, "other")

    booking_decision = _norm(payload.get("booking_decision"))
    decline_reason = _norm(payload.get("decline_reason"))

    if outcome == "other":
        if booking_decision in {"yes", "y", "true"}:
            outcome = "booked"
        elif booking_decision in {"no", "n", "false"}:
            if "rate" in decline_reason or "price" in decline_reason:
                outcome = "negotiation_failed"
            elif decline_reason:
                outcome = "declined"

    sentiment_raw = _norm(payload.get("sentiment"))
    if sentiment_raw in CANONICAL_SENTIMENTS:
        sentiment = sentiment_raw
    elif sentiment_raw in {"pos", "happy"}:
        sentiment = "positive"
    elif sentiment_raw in {"neg", "angry", "frustrated"}:
        sentiment = "negative"
    else:
        sentiment = SENTIMENT_FALLBACK_BY_OUTCOME.get(outcome, "neutral")

    eligible = _to_bool(payload.get("eligible"))
    if eligible is None and outcome == "ineligible_carrier":
        eligible = False
    if eligible is None and outcome in {"booked", "transferred", "negotiation_failed", "declined"}:
        eligible = True

    notes = payload.get("notes")
    duration = _to_int(payload.get("call_duration"), default=0)
    if duration and not notes:
        notes = f"call_duration={duration}s"

    return CanonicalCall(
        mc_number=str(payload["mc_number"]) if payload.get("mc_number") else None,
        carrier_name=payload.get("carrier_name") or None,
        eligible=eligible,
        load_id=payload.get("reference_number") or payload.get("load_id"),
        outcome=outcome,
        sentiment=sentiment,
        rounds=_to_int(payload.get("rounds"), default=0),
        loadboard_rate=_to_float(payload.get("loadboard_rate")),
        final_carrier_offer=_to_float(payload.get("final_carrier_offer")),
        agreed_price=_to_float(payload.get("agreed_price")),
        transcript=payload.get("transcript") or None,
        notes=notes,
        raw=payload,
    )
