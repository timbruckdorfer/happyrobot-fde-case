"""Unit tests for the negotiation policy."""

from __future__ import annotations

import pytest

from app.services.negotiation import evaluate_offer


def test_accepts_offer_within_band():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=1000, round_number=1)
    assert d.decision == "accept"
    assert d.counter_price is None


def test_accepts_offer_at_floor():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=920, round_number=1)
    assert d.decision == "accept"


def test_accepts_offer_at_ceiling():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=1100, round_number=1)
    assert d.decision == "accept"


def test_counters_when_below_floor_round_1():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=800, round_number=1)
    assert d.decision == "counter"
    assert d.counter_price is not None
    assert d.counter_price >= 920


def test_counters_when_above_ceiling_round_1():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=1300, round_number=1)
    assert d.decision == "counter"
    assert d.counter_price is not None
    assert d.counter_price <= 1100


def test_round_2_uses_last_broker_price():
    first = evaluate_offer(loadboard_rate=1000, carrier_offer=800, round_number=1)
    second = evaluate_offer(
        loadboard_rate=1000,
        carrier_offer=850,
        round_number=2,
        last_broker_price=first.counter_price,
    )
    assert second.decision in {"counter", "accept"}


def test_final_round_rejects_when_below_floor():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=800, round_number=3)
    assert d.decision == "reject"
    assert d.counter_price == 920


def test_final_round_accepts_within_band():
    d = evaluate_offer(loadboard_rate=1000, carrier_offer=950, round_number=3)
    assert d.decision == "accept"


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        evaluate_offer(loadboard_rate=0, carrier_offer=100, round_number=1)
    with pytest.raises(ValueError):
        evaluate_offer(loadboard_rate=100, carrier_offer=0, round_number=1)
    with pytest.raises(ValueError):
        evaluate_offer(loadboard_rate=100, carrier_offer=100, round_number=0)
