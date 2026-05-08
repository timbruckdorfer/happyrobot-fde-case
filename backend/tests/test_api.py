"""Smoke tests for the API surface (auth, search, evaluate, calls, metrics)."""

from __future__ import annotations


def test_healthz_is_public(client):
    resp = client.get("/healthz", headers={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_requires_api_key(client):
    resp = client.post("/api/search_loads", json={}, headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_search_loads_returns_seed_data(client):
    resp = client.post("/api/search_loads", json={"max_results": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert len(body["loads"]) == 3


def test_search_loads_filters_by_equipment(client):
    resp = client.post("/api/search_loads", json={"equipment_type": "Reefer", "max_results": 10})
    assert resp.status_code == 200
    for load in resp.json()["loads"]:
        assert "reefer" in load["equipment_type"].lower()


def test_get_load_by_id(client):
    resp = client.get("/api/loads/REF1001")
    assert resp.status_code == 200
    assert resp.json()["load_id"] == "REF1001"


def test_get_load_is_case_insensitive(client):
    """Voice agents sometimes lowercase identifiers when generating tool args.
    The DB stores canonical "REF1001"; the endpoint should still resolve it
    when the agent passes "ref1001"."""
    resp = client.get("/api/loads/ref1001")
    assert resp.status_code == 200
    assert resp.json()["load_id"] == "REF1001"

    resp = client.get("/api/loads/Ref1001")
    assert resp.status_code == 200
    assert resp.json()["load_id"] == "REF1001"


def test_get_load_404(client):
    resp = client.get("/api/loads/DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_evaluate_offer_is_case_insensitive_on_load_id(client):
    """Same case-insensitivity guarantee as GET /api/loads."""
    resp = client.post(
        "/api/evaluate_offer",
        json={"load_id": "ref1001", "carrier_offer": 2450, "round": 1},
    )
    assert resp.status_code == 200, resp.text


def test_evaluate_offer_accept(client):
    resp = client.post(
        "/api/evaluate_offer",
        json={"load_id": "REF1001", "carrier_offer": 2450, "round": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "accept"


def test_evaluate_offer_counter(client):
    resp = client.post(
        "/api/evaluate_offer",
        json={"load_id": "REF1001", "carrier_offer": 1500, "round": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "counter"
    assert body["counter_price"] >= body["floor"]


def test_calls_ingest_and_metrics(client):
    resp = client.post(
        "/api/calls",
        json={
            "mc_number": "123456",
            "carrier_name": "Test Carrier",
            "eligible": True,
            "load_id": "REF1001",
            "outcome": "booked",
            "sentiment": "positive",
            "rounds": 2,
            "loadboard_rate": 2450,
            "final_carrier_offer": 2350,
            "agreed_price": 2400,
            "transcript": "...",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "booked"

    metrics = client.get("/api/metrics").json()
    assert metrics["total_calls"] >= 1
    assert metrics["booked_calls"] >= 1
    assert metrics["conversion_rate"] > 0
