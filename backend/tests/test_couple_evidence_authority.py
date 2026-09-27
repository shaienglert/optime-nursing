from app.services.client_intent_runtime import evaluate_candidate_intent


def test_possible_couple_unit_does_not_satisfy_coresidence_must():
    row = {
        "canonical_type": "ASSISTED_LIVING_RFG",
        "housing_modalities": [],
        "provider_evidence": [{"couple_unit_possible": True, "couple_coresidence_verified": False}],
        "agent_evidence": [],
    }
    intent = {"must_haves": [{"key": "COUPLE_CORESIDENCE"}], "nice_to_haves": []}
    fit = evaluate_candidate_intent(row, intent)
    assert "COUPLE_CORESIDENCE" not in fit["must_pass"]
