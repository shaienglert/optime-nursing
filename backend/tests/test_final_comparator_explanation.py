from copy import deepcopy

from app.services.regulatory_quality_layer import explain_ranked_pair, rank_with_evidence_layer


DIMENSIONS = (("family_fit", "Better fit for the family's request."),)


def row(identity, fit=0, grade=None, source="PUBLIC_REVIEWS", rating=None):
    return {"canonical_facility_id": identity, "family_key": fit,
            "regulatory_history": {"latest_known_grade": grade},
            "client_intent_fit": {"public_reputation": {"rating": rating, "source": source}}}


def rank(rows):
    return rank_with_evidence_layer(rows, lambda item: (item["family_key"],))


def test_family_criterion_wins_before_better_regulatory_grade():
    higher, lower = rank([row("a", 0, "C"), row("b", 1, "A")])
    comparison = explain_ranked_pair(higher, lower, DIMENSIONS)
    assert comparison["decision_dimension"] == "family_fit"
    assert comparison["comparison_evidence"]["source"] == "FINAL_COMPARATOR_SNAPSHOT"


def test_same_family_group_explains_shared_grade_evidence():
    higher, lower = rank([row("b", grade="B"), row("a", grade="A")])
    comparison = explain_ranked_pair(higher, lower, DIMENSIONS)
    assert comparison["decision_dimension"] == "alis_latest_grade"
    assert comparison["comparison_evidence"]["source_family"] == "NV_ALIS"
    assert comparison["equal_dimensions"] == ["family_fit"]


def test_missing_grade_cannot_become_an_explanation_or_penalty():
    rows = rank([row("b", grade=None), row("a", grade="A")])
    assert rows[0]["rank_group_signature"] == rows[1]["rank_group_signature"]
    assert explain_ranked_pair(*rows, DIMENSIONS)["decision_dimension"] == "true_tie"


def test_incomparable_review_sources_remain_a_true_tie():
    rows = rank([row("a", rating=5, source="One source"), row("b", rating=3, source="Another source")])
    assert explain_ranked_pair(*rows, DIMENSIONS)["decision_dimension"] == "true_tie"


def test_later_record_change_cannot_rewrite_original_comparison():
    rows = rank([row("a", grade="A"), row("b", grade="B")])
    before = explain_ranked_pair(*rows, DIMENSIONS)
    rows[0]["regulatory_history"]["latest_known_grade"] = "D"
    rows[1]["regulatory_history"]["latest_known_grade"] = "A"
    assert explain_ranked_pair(*rows, DIMENSIONS) == before


def test_nested_evidence_branch_uses_the_first_actual_difference():
    rows = rank([row("a", grade="A", rating=5), row("b", grade="A", rating=4), row("c", grade="B", rating=5)])
    assert explain_ranked_pair(rows[0], rows[1], DIMENSIONS)["decision_dimension"] == "public_rating"
    assert explain_ranked_pair(rows[1], rows[2], DIMENSIONS)["decision_dimension"] == "alis_latest_grade"


def test_reversed_pair_or_changed_comparator_shape_does_not_invent_reason():
    rows = rank([row("a", 0), row("b", 1)])
    assert explain_ranked_pair(rows[1], rows[0], DIMENSIONS) is None
    assert explain_ranked_pair(*rows, ()) is None


def test_no_snapshot_never_reconstructs_comparison_from_other_evidence():
    assert explain_ranked_pair(row("a", grade="A"), row("b", grade="D"), DIMENSIONS) is None


def test_explanation_is_read_only_and_name_never_decides_rank():
    rows = rank([row("z"), row("a")])
    before = deepcopy(rows)
    comparison = explain_ranked_pair(*rows, DIMENSIONS)
    assert comparison["decision_dimension"] == "true_tie"
    assert rows == before


def test_snapshot_rejects_same_length_reordered_names():
    dimensions = (("first", "First"), ("second", "Second"))
    rows = rank_with_evidence_layer([row("a", 0), row("b", 1)],
                                   lambda r: (r["family_key"], 0), base_dimensions=dimensions)
    assert explain_ranked_pair(*rows, dimensions)
    assert explain_ranked_pair(*rows, dimensions[::-1]) is None


def test_final_component_names_are_pinned_to_real_key_order():
    from app.services.must_ai_nice_pipeline import _FINAL_BASE_DIMENSIONS, _layered_rank
    candidate = {"budget_exception": True,
                 "human_person_fit": {"community_size": {"fit_score": 13}},
                 "care_setting_fit": {"status": "OVERLEVEL"},
                 "client_intent_fit": {"hard_gate": "FAIL", "nice_match": ["a", "b", "c", "d"],
                                       "nice_mismatch": ["x", "y", "z", "q", "r"],
                                       "nice_fit_scores": {"COMMUNITY_ENVIRONMENT_MATCH": 17}},
                 "nearby_place_fit": {"status": "KNOWN", "importance": "Important", "fit_band": 7,
                                      "average_distance_miles": 23}}
    snapshot = _layered_rank([candidate])[0]["__rank_comparison_trace"]
    assert dict(zip((name for name, _ in _FINAL_BASE_DIMENSIONS), snapshot["base_values"])) == {
        "strict_budget_before_expansion": 1, "community_preference_evidence": 0,
        "community_preference_fit": -13., "must_gate": 2, "care_setting_fit": 2,
        "verified_preference_matches": -4, "verified_preference_mismatches": 5,
        "community_environment_evidence": 0, "community_environment_fit": -17.,
        "nearby_comparison_scope": 0, "requested_nearby_fit": -7, "requested_nearby_distance": 23.}
