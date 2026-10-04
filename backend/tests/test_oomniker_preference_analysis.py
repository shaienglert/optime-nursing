from copy import deepcopy
import pytest

from app.services.oomniker_preference_analysis import analyze_preferences
from app.services.must_ai_nice_pipeline import _layered_rank

KEY = "COMMUNITY_ENVIRONMENT_MATCH"
INTENT = {"must_haves": [{"key": "ADL_SUPPORT_AVAILABLE"}], "nice_to_haves": [{"key": KEY}]}
PROFILE = {"humanIntelligenceV2": {"personalityProfile": {"communitySizePreference": "Small and familiar"}}}

def row(fid, size="SMALL_COMMUNITY", gate="PASS", quality=2):
    score = 100 if size == "SMALL_COMMUNITY" else 60
    return {"canonical_facility_id": fid, "facility_name": fid, "care_setting_fit": {"status": "PRIMARY_FIT"},
            "human_person_fit": {"community_size": {"community_size_band": size, "fit_score": score, "preference": "SMALL"}},
            "client_intent_fit": {"hard_gate": gate, "must_pass": ["ADL_SUPPORT_AVAILABLE"], "must_fail": [], "must_unknown": [],
                                  "nice_match": [KEY] if score == 100 else [], "nice_mismatch": [KEY] if score != 100 else [],
                                  "nice_unknown": [], "nice_fit_scores": {KEY: score}},
            "regulatory_quality_evidence": {"inspection_rating": {"value": quality, "source_family": "TEST_GOVERNMENT"}}}

def pool(extra=2):
    return [row(f"small-{i}") for i in range(5)] + [row(f"medium-{i}", "MEDIUM_COMMUNITY", quality=5) for i in range(extra)]

def analyze(rows, intent=None, **kwargs):
    return analyze_preferences(rows, intent or deepcopy(INTENT), deepcopy(PROFILE), _layered_rank, **kwargs)

def test_two_quality_alternatives_from_full_pool_and_original_order_unchanged():
    rows = pool()
    original = deepcopy(rows)
    baseline = [_layered_rank(deepcopy(rows))[i]["canonical_facility_id"] for i in range(5)]
    out = analyze(rows)
    suggestion = next(s for s in out["suggestions"] if s["alternative_value"] == "Medium")
    assert suggestion["new_recommendation_count"] == 2
    assert suggestion["additional_eligible_count"] == 0
    assert {r["canonical_facility_id"] for r in suggestion["candidates"]} == {"medium-0", "medium-1"}
    assert all(c["quality_advantage"]["parameter"] == "inspection_rating" for c in suggestion["candidates"])
    assert baseline == [f"small-{i}" for i in range(5)]
    assert rows == original
    assert out["parameters"][0]["excluded_by_preference_count"] == 0
    assert out["parameters"][0]["eligible_below_display_count"] == 2

@pytest.mark.parametrize("extra", [0, 1])
def test_no_offer_for_fewer_than_two(extra):
    assert analyze(pool(extra))["suggestions"] == []

@pytest.mark.parametrize("gate", ["FAIL", "PENDING_VERIFICATION"])
def test_must_blocked_communities_never_count(gate):
    rows = pool()
    for item in rows[5:]:
        item["client_intent_fit"]["hard_gate"] = gate
    assert not analyze(rows)["suggestions"]

def test_unknown_other_preference_and_dynamic_evidence_do_not_prove_match():
    rows = pool()
    intent = deepcopy(INTENT)
    intent["nice_to_haves"].append({"key": "CLASSICAL_MUSIC_ACCESS"})
    for item in rows:
        item["client_intent_fit"]["nice_unknown"].append("CLASSICAL_MUSIC_ACCESS")
    assert not analyze(rows, intent)["suggestions"]
    assert not analyze(pool(), dynamic_preference_count=1)["suggestions"]

def test_duplicate_id_and_missing_quality_do_not_create_advice():
    rows = pool()
    rows[-1]["canonical_facility_id"] = rows[-2]["canonical_facility_id"]
    assert analyze(rows)["status"] == "INVALID_IDENTITIES"
    rows = pool()
    for item in rows:
        item.pop("regulatory_quality_evidence")
    assert not analyze(rows)["suggestions"]

def test_must_preference_overlap_is_protected():
    intent = deepcopy(INTENT)
    intent["must_haves"].append({"key": KEY})
    assert not analyze(pool(), intent)["suggestions"]

def test_same_measure_from_different_sources_is_not_quality_advantage():
    rows = pool()
    for item in rows[5:]:
        item["regulatory_quality_evidence"]["inspection_rating"]["source_family"] = "UNRELATED"
    assert not analyze(rows)["suggestions"]

def test_change_in_true_tie_listing_order_does_not_count_as_gain():
    rows = pool(6)
    # The six medium communities are tied across the display boundary.
    assert not analyze(rows)["suggestions"]

def test_budget_partition_survives_preference_change():
    rows = pool()
    for item in rows[5:]:
        item["budget_exception"] = True
    assert not analyze(rows)["suggestions"]

def test_quality_does_not_cherry_pick_after_worse_inspection_rating():
    rows = pool()
    for item in rows[5:]:
        item["regulatory_quality_evidence"]["inspection_rating"]["value"] = 1
        item["regulatory_quality_evidence"]["rn_hours_per_resident_day"] = {"value": 10, "source_family": "TEST_GOVERNMENT"}
    for item in rows[:5]:
        item["regulatory_quality_evidence"]["rn_hours_per_resident_day"] = {"value": 1, "source_family": "TEST_GOVERNMENT"}
    assert not analyze(rows)["suggestions"]
