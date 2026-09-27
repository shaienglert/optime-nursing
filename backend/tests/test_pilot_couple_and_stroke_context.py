from app.services.client_intent_runtime import evaluate_candidate_intent
from app.services.decision_engine_core import build_patient_needs_profile


def _intent():
    return {"must_haves": [{"key": "COUPLE_CORESIDENCE"}], "nice_to_haves": []}


def test_pilot_couple_policy_is_governed_evidence():
    for value, bucket in [(True, "must_pass"), (False, "must_fail"), (None, "must_unknown")]:
        row = {"synthetic_pilot": True, "accepts_couples": value}
        result = evaluate_candidate_intent(row, _intent())
        assert "COUPLE_CORESIDENCE" in result[bucket]


def test_real_facility_cannot_inherit_pilot_couple_policy():
    result = evaluate_candidate_intent({"accepts_couples": True}, _intent())
    assert "COUPLE_CORESIDENCE" in result["must_unknown"]


def test_past_stroke_is_not_a_current_rehabilitation_need():
    profile = build_patient_needs_profile(
        {}, "Father needs help bathing and dressing after a stroke; mother is independent."
    )
    ids = {need["parameter_id"] for need in profile["needs"]}
    assert "adl_support" in ids
    assert "post_stroke_neuro_evidence" not in ids


def test_explicit_stroke_rehab_is_a_current_rehabilitation_need():
    profile = build_patient_needs_profile(
        {}, "Father needs stroke rehabilitation and help bathing."
    )
    ids = {need["parameter_id"] for need in profile["needs"]}
    assert "post_stroke_neuro_evidence" in ids
