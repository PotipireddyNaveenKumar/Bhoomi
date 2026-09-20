import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_simulation_endpoints_functional_equivalence():
    """
    Stabilization Batch 2 Verification:
    Verify that POST /api/v1/simulation/what-if and POST /api/v1/simulation/run
    are functionally identical in input schema, calculation results, and response structure.
    """
    payload = {
        "crop_name": "Chilli",
        "area_acres": 3.0,
        "baseline_yield_quintals_per_acre": 10.0,
        "baseline_market_price_per_quintal": 12000.0,
        "baseline_cultivation_cost": 70000.0,
        "price_change_percent": -20.0,
        "yield_change_percent": 10.0,
        "cost_change_percent": 5.0
    }

    res_what_if = client.post("/api/v1/simulation/what-if", json=payload)
    res_run = client.post("/api/v1/simulation/run", json=payload)

    assert res_what_if.status_code == 200, f"what-if failed: {res_what_if.text}"
    assert res_run.status_code == 200, f"run failed: {res_run.text}"

    data_what_if = res_what_if.json()
    data_run = res_run.json()

    assert data_what_if == data_run, "Outputs between /what-if and /run diverge!"
    assert data_what_if["crop_name"] == "Chilli"
    assert "baseline" in data_what_if
    assert "simulated_scenario" in data_what_if
    assert "risk_impact_explanation" in data_what_if
    assert "recommended_hedging_actions" in data_what_if
    assert float(data_what_if["baseline"]["net_profit"]) == 290000.0

def test_simulation_endpoints_validation_equivalence():
    """
    Verify that invalid payloads produce identical 422 validation errors on both endpoints.
    """
    invalid_payload = {
        "crop_name": "Chilli"
        # missing required area_acres, baseline_yield_quintals_per_acre, etc.
    }

    res_what_if = client.post("/api/v1/simulation/what-if", json=invalid_payload)
    res_run = client.post("/api/v1/simulation/run", json=invalid_payload)

    assert res_what_if.status_code == 422
    assert res_run.status_code == 422
    assert len(res_what_if.json()["detail"]) == len(res_run.json()["detail"])
