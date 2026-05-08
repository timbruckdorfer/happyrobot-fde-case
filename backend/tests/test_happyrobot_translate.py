"""Unit tests for the HappyRobot end-of-call translation layer."""

from __future__ import annotations

import pytest

from app.services.happyrobot_translate import translate


def test_success_tag_maps_to_booked():
    out = translate(
        {
            "classification": "Success",
            "reference_number": "REF1001",
            "mc_number": "123456",
            "carrier_name": "ABC Trucking",
            "booking_decision": "yes",
            "agreed_price": 2400,
            "loadboard_rate": 2450,
            "rounds": 1,
            "transcript": "...",
        }
    )
    assert out.outcome == "booked"
    assert out.sentiment == "positive"
    assert out.eligible is True
    assert out.load_id == "REF1001"
    assert out.agreed_price == 2400.0
    assert out.rounds == 1


def test_typo_sucess_still_maps_to_booked():
    out = translate({"classification": "Sucess"})
    assert out.outcome == "booked"


def test_rate_too_high_maps_to_negotiation_failed():
    out = translate(
        {
            "classification": "Rate too high",
            "booking_decision": "no",
            "decline_reason": "rate too high",
        }
    )
    assert out.outcome == "negotiation_failed"
    assert out.sentiment == "negative"


def test_not_interested_maps_to_declined():
    out = translate({"classification": "Not interested", "booking_decision": "no"})
    assert out.outcome == "declined"
    assert out.sentiment == "neutral"


def test_ineligible_carrier_sets_eligible_false():
    out = translate({"classification": "Ineligible carrier"})
    assert out.outcome == "ineligible_carrier"
    assert out.eligible is False


def test_no_match_outcome():
    out = translate({"classification": "No match"})
    assert out.outcome == "no_match"


def test_unknown_classification_uses_booking_decision_fallback():
    out = translate(
        {
            "classification": "WeirdNewTag",
            "booking_decision": "yes",
        }
    )
    assert out.outcome == "booked"


def test_unknown_classification_with_decline_reason_falls_back():
    out = translate(
        {
            "classification": "WeirdNewTag",
            "booking_decision": "no",
            "decline_reason": "rate is too low for me",
        }
    )
    assert out.outcome == "negotiation_failed"


def test_unknown_classification_falls_back_to_other():
    out = translate({"classification": "NoIdea"})
    assert out.outcome == "other"


def test_explicit_sentiment_wins_over_default():
    out = translate({"classification": "Success", "sentiment": "negative"})
    assert out.sentiment == "negative"


def test_call_duration_lands_in_notes_when_no_other_notes():
    out = translate({"classification": "Success", "call_duration": 245})
    assert "call_duration=245s" in (out.notes or "")


def test_existing_notes_preserved():
    out = translate(
        {"classification": "Success", "call_duration": 245, "notes": "manual note"}
    )
    assert out.notes == "manual note"


def test_string_numbers_coerced():
    out = translate(
        {
            "classification": "Success",
            "agreed_price": "2400.50",
            "rounds": "2",
            "loadboard_rate": "2450",
        }
    )
    assert out.agreed_price == 2400.5
    assert out.rounds == 2
    assert out.loadboard_rate == 2450.0


def test_list_transcript_serialized_to_json_string():
    """HappyRobot's webhook node forwards transcript as a structured array
    when ``preserveDataTypes`` is enabled. SQLite's TEXT column can't bind a
    Python list, so the translate layer must serialize it to a JSON string."""
    transcript = [
        {"role": "assistant", "content": "Hi, this is Happy Robot Logistics."},
        {"role": "user", "content": "Hi, calling about REF1001."},
    ]
    out = translate({"classification": "Success", "transcript": transcript})
    assert isinstance(out.transcript, str)
    # Round-trips back to the original structure.
    import json as _json

    assert _json.loads(out.transcript) == transcript


def test_dict_transcript_serialized_to_json_string():
    """Same defensive coercion for dict-shaped transcripts."""
    transcript = {"messages": [{"role": "user", "content": "hi"}]}
    out = translate({"classification": "Success", "transcript": transcript})
    assert isinstance(out.transcript, str)


def test_empty_transcript_normalizes_to_none():
    """Empty string transcript should land as None, not an empty string."""
    out = translate({"classification": "Success", "transcript": ""})
    assert out.transcript is None


def test_missing_classification_raises():
    with pytest.raises(ValueError):
        translate({"mc_number": "123"})


def test_load_id_alias_supported():
    out = translate({"classification": "Success", "load_id": "REF1003"})
    assert out.load_id == "REF1003"


def test_endpoint_round_trip(client):
    resp = client.post(
        "/api/calls/happyrobot",
        json={
            "classification": "Success",
            "sentiment": "Positive",
            "reference_number": "REF1002",
            "mc_number": "234567",
            "carrier_name": "ABC Trucking",
            "booking_decision": "yes",
            "agreed_price": 2050,
            "loadboard_rate": 2100,
            "final_carrier_offer": 2050,
            "rounds": 2,
            "transcript": "...",
            "call_duration": 180,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "booked"
    assert body["sentiment"] == "positive"
    assert body["load_id"] == "REF1002"
    assert body["mc_number"] == "234567"
    assert body["agreed_price"] == 2050
    assert body["rounds"] == 2


def test_endpoint_rejects_payload_without_classification(client):
    resp = client.post("/api/calls/happyrobot", json={"mc_number": "123"})
    assert resp.status_code == 422
