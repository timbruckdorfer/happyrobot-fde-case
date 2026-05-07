"""Round-aware negotiation policy.

Goals:
- Protect broker margin via a configurable floor (% of loadboard rate).
- Be willing to come up modestly via a configurable ceiling.
- Cap rounds server-side so the agent can't accidentally negotiate forever.

Decisions:
- "accept": carrier_offer is acceptable; final price = carrier_offer.
- "counter": broker proposes counter_price. Carrier may respond next round.
- "reject": no deal. Used only on the final round when we still aren't aligned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal["accept", "counter", "reject"]


@dataclass
class OfferDecision:
    decision: Decision
    counter_price: float | None
    rationale: str
    round: int
    final_round: int


def evaluate_offer(
    *,
    loadboard_rate: float,
    carrier_offer: float,
    round_number: int,
    floor_pct: float = 0.92,
    ceiling_pct: float = 1.10,
    max_rounds: int = 3,
    last_broker_price: float | None = None,
) -> OfferDecision:
    if loadboard_rate <= 0:
        raise ValueError("loadboard_rate must be positive")
    if carrier_offer <= 0:
        raise ValueError("carrier_offer must be positive")
    if round_number < 1:
        raise ValueError("round_number must be >= 1")

    floor = round(loadboard_rate * floor_pct, 2)
    ceiling = round(loadboard_rate * ceiling_pct, 2)
    broker_price = last_broker_price if last_broker_price is not None else loadboard_rate

    if floor <= carrier_offer <= ceiling:
        return OfferDecision(
            decision="accept",
            counter_price=None,
            rationale=f"Offer ${carrier_offer:.2f} within acceptable band ${floor:.2f}-${ceiling:.2f}.",
            round=round_number,
            final_round=max_rounds,
        )

    if round_number >= max_rounds:
        return OfferDecision(
            decision="reject",
            counter_price=floor,
            rationale=(
                f"Final round reached. Best we can do is ${floor:.2f}; "
                f"carrier offered ${carrier_offer:.2f}."
            ),
            round=round_number,
            final_round=max_rounds,
        )

    if carrier_offer < floor:
        midpoint = (broker_price + carrier_offer) / 2
        counter = max(round(midpoint, 2), floor)
        rationale = (
            f"Offer ${carrier_offer:.2f} below floor ${floor:.2f}. "
            f"Countering at ${counter:.2f} (midpoint clamped to floor)."
        )
    else:
        midpoint = (broker_price + carrier_offer) / 2
        counter = min(round(midpoint, 2), ceiling)
        rationale = (
            f"Offer ${carrier_offer:.2f} above ceiling ${ceiling:.2f}. "
            f"Countering at ${counter:.2f} (midpoint clamped to ceiling)."
        )

    return OfferDecision(
        decision="counter",
        counter_price=counter,
        rationale=rationale,
        round=round_number,
        final_round=max_rounds,
    )
