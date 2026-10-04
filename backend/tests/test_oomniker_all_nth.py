from copy import deepcopy
import pytest

from app.services.must_ai_nice_pipeline import _layered_rank
from app.services.oomniker_preference_analysis import analyze_preferences

KEYS = ["RICH_CULTURE_AND_ACTIVITIES", "CLASSICAL_MUSIC_ACCESS", "TRANSPORTATION_AND_OUTINGS",
        "DINING_EXPERIENCE", "KOSHER_MEALS", "SOCIAL_INTERACTION_FREQUENCY"]

def fixture(key, extra=2):
    intent = {"must_haves": [{"key": "ADL_SUPPORT_AVAILABLE"}], "nice_to_haves": [{"key": key}]}
    rows = []
    for index in range(5 + extra):
        match = index < 5
        rows.append({"canonical_facility_id": str(index), "facility_name": f"Community {index}",
            "care_setting_fit": {"status": "PRIMARY_FIT"},
            "client_intent_fit": {"hard_gate": "PASS", "must_pass": ["ADL_SUPPORT_AVAILABLE"],
                "must_fail": [], "must_unknown": [], "nice_match": [key] if match else [],
                "nice_mismatch": [] if match else [key], "nice_unknown": [],
                "nice_fit_scores": {key: 100 if match else 0}},
            "regulatory_quality_evidence": {"inspection_rating": {"value": 2 if match else 5,
                "source_family": "TEST_GOVERNMENT"}}})
    return rows, intent, {"budget": 7000}

@pytest.mark.parametrize("key", KEYS)
def test_every_nth_can_offer_two_measured_alternatives_and_replay_the_same_change(key):
    from app.services.oomniker_nth_contract import apply_accepted_nth_changes
    rows, intent, profile = fixture(key)
    before = deepcopy(rows)
    out = analyze_preferences(rows, intent, profile, _layered_rank)
    suggestion = next(s for s in out["suggestions"] if s["parameter"] == key)
    assert suggestion["new_recommendation_count"] == 2
    assert rows == before
    changed = deepcopy(rows)
    audit = apply_accepted_nth_changes(changed, intent, profile, [suggestion["acceptance"]])
    assert audit["applied"] == [key]
    ids = {r["canonical_facility_id"] for r in _layered_rank(changed)[:5]}
    assert {c["canonical_facility_id"] for c in suggestion["candidates"]} <= ids
    for old, new in zip(before, changed):
        for field in ("hard_gate", "must_pass", "must_fail", "must_unknown"):
            assert old["client_intent_fit"][field] == new["client_intent_fit"][field]
        assert old["regulatory_quality_evidence"] == new["regulatory_quality_evidence"]

    # Verify the same contract through the production selection pipeline, not
    # just the advisor's isolated comparator, and reproduce the undo result.
    from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline
    def search(consent=None):
        result = {"results": deepcopy(before), "decision_intelligence": {"client_intent": deepcopy(intent)}}
        return apply_must_ai_nice_pipeline(result, profile, "", 50, accepted_preference_changes=consent)
    baseline = search()
    rerun = search([suggestion["acceptance"]])
    assert {c["canonical_facility_id"] for c in suggestion["candidates"]} <= {
        r["canonical_facility_id"] for r in rerun["results"][:5]}
    assert rerun["decision_intelligence"]["client_intent"]["must_haves"] == intent["must_haves"]
    assert rerun["must_eligible_count"] == baseline["must_eligible_count"] == len(rows)
    assert rerun["decision_intelligence"]["oomniker_client_consent"]["applied"] == [key]
    assert [r["canonical_facility_id"] for r in search()["results"]] == [r["canonical_facility_id"] for r in baseline["results"]]

def test_acceptance_is_bound_to_the_inputs_and_cannot_relax_a_must_or_budget():
    from app.services.oomniker_nth_contract import apply_accepted_nth_changes
    rows, intent, profile = fixture("KOSHER_MEALS")
    advice = analyze_preferences(rows, intent, profile, _layered_rank)["suggestions"][0]
    before = deepcopy(rows)
    assert not apply_accepted_nth_changes(rows, intent, {"budget": 8000}, [advice["acceptance"]])["applied"]
    intent["must_haves"].append({"key": "KOSHER_MEALS"})
    assert not apply_accepted_nth_changes(rows, intent, profile, [advice["acceptance"]])["applied"]
    assert rows == before
    for key in ("BUDGET_FIT", "AVAILABILITY_FIT", "SECURED_UNIT_AVAILABLE", "maximum_distance_miles"):
        forged = {"parameter": key, "input_fingerprint": advice["acceptance"]["input_fingerprint"]}
        assert not apply_accepted_nth_changes(rows, intent, profile, [forged])["applied"]

def test_unknown_one_new_candidate_and_unmatched_remaining_preference_never_create_offer():
    for extra in (0, 1):
        rows, intent, profile = fixture("DINING_EXPERIENCE", extra)
        assert not analyze_preferences(rows, intent, profile, _layered_rank)["suggestions"]
    rows, intent, profile = fixture("DINING_EXPERIENCE")
    intent["nice_to_haves"].append({"key": "CLASSICAL_MUSIC_ACCESS"})
    for row in rows:
        row["client_intent_fit"]["nice_unknown"].append("CLASSICAL_MUSIC_ACCESS")
    assert not analyze_preferences(rows, intent, profile, _layered_rank)["suggestions"]

def test_arbitrary_dynamic_nth_is_analyzed_but_no_rank_effect_is_not_an_offer():
    rows, intent, profile = fixture("DINING_EXPERIENCE")
    model = {"preferences": [{"preference_id": "pref:quiet", "importance": "NICE",
        "client_expression": "Quiet nights", "mapped_parameters": []}]}
    out = analyze_preferences(rows, intent, profile, _layered_rank,
        dynamic_preferences=model, dynamic_preference_count=1)
    item = next(p for p in out["parameters"] if p["parameter"] == "pref:quiet")
    assert item["label"] == "Quiet nights"
    assert item["status"] == "NO_VERIFIED_RANKING_EFFECT"
    assert item["new_recommendation_count"] == 0
    assert not out["suggestions"]
