"""The intake must price its actual search, never another market or funding path."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from app.services.market_price_floor import minimum_price_for_questionnaire

PERSONAS = json.loads((Path(__file__).resolve().parents[2] / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"]

@pytest.fixture(autouse=True)
def pilot(monkeypatch):
    monkeypatch.setenv("OPTIME_CANONICAL_MARKET", "synthetic-pilot")
    monkeypatch.setenv("OOMNIK_PILOT_FACILITY_LIMIT", "500")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "1")
    with patch("app.services.human_intelligence_runtime_verified._call_semantic_ai", side_effect=AssertionError("Intake preview must not call the interpreter")):
        yield

@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_current_catalog_and_care_are_used_before_budget(persona):
    from app.services.facility_parameter_service import get_canonical_facility_index
    from app.services.location_radius import annotate_distances, resolve_reference_point
    result = minimum_price_for_questionnaire(persona["questionnaire_state"])
    assert result["status"] == "KNOWN"
    assert result["minimum_monthly_price"] > 100
    assert result["synthetic_pilot"] is True
    assert result["location_scope"]["applied"] is True
    fid = result["canonical_facility_id"]
    index = get_canonical_facility_index()
    row = {"canonical_facility_id": fid}
    reference = resolve_reference_point(persona["questionnaire_state"], index.values())
    annotate_distances([row], reference, index)
    assert row["distance_miles"] <= float(persona["oracle"]["distance"])

def test_budget_and_medicaid_cannot_shape_the_private_care_floor():
    state = PERSONAS[5]["questionnaire_state"]
    values = [minimum_price_for_questionnaire({**state, "budget": budget, "medicaidStatus": funding})
              for budget, funding in [(1, "Not eligible"), (3000, "Application pending"), (100000, "Approved")]]
    assert len({v["minimum_monthly_price"] for v in values}) == 1
    assert values[0]["minimum_budget_is_binding"] is True
    assert all(not v["minimum_budget_is_binding"] for v in values[1:])
    assert values[1]["funding_pathway"] == "MEDICAID_COST_REQUIRES_VERIFICATION"

def test_empty_radius_does_not_fall_back_to_the_whole_database():
    result = minimum_price_for_questionnaire({**PERSONAS[0]["questionnaire_state"], "referenceLatitude": 40, "referenceLongitude": -110})
    assert result["minimum_monthly_price"] is None
    assert result["minimum_budget_is_binding"] is False

def test_unresolved_address_never_claims_an_area_price():
    state = {**PERSONAS[0]["questionnaire_state"], "referenceAddress": "123 Unresolved Street", "referenceLocationValue": "Unknown area", "locationCity": ""}
    result = minimum_price_for_questionnaire(state)
    assert result["status"] == "LOCATION_UNRESOLVED"
    assert result["minimum_monthly_price"] is None
