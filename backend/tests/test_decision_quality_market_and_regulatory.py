from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key


def _intent(query: str):
    return build_client_intent({}, query, {"signals": {}, "household": {}}, {"signals": {}})


def test_unqualified_las_vegas_search_includes_henderson_valley_option():
    intent = _intent("Looking for senior living in Las Vegas")
    row = {"city": "Henderson", "state": "NV", "canonical_type": "INDEPENDENT_LIVING", "housing_modalities": ["INDEPENDENT_LIVING"]}
    fit = evaluate_candidate_intent(row, intent)
    assert "LAS_VEGAS" in fit["must_pass"]
    assert fit["hard_gate"] != "FAIL"


def test_explicit_city_limits_still_excludes_henderson():
    intent = _intent("Looking only within Las Vegas city limits")
    row = {"city": "Henderson", "state": "NV", "canonical_type": "INDEPENDENT_LIVING", "housing_modalities": ["INDEPENDENT_LIVING"]}
    fit = evaluate_candidate_intent(row, intent)
    assert "LAS_VEGAS_CITY_LIMITS" in fit["must_fail"]
    assert fit["hard_gate"] == "FAIL"


def _rank_row(name: str, canonical_type: str, modalities, history):
    return {
        "facility_name": name,
        "canonical_type": canonical_type,
        "housing_modalities": modalities,
        "care_setting_fit": {"status": "POSSIBLE_FIT"},
        "client_intent_fit": {
            "hard_gate": "PASS", "nice_match": [], "nice_fit_scores": {},
            "public_reputation": {}, "relevant_evidence_known_count": 1,
            "relevant_evidence_unknown_count": 0,
        },
        "regulatory_history": history,
    }


def test_non_applicable_rfg_grade_does_not_penalize_pure_independent_living():
    pure_il = _rank_row("Pure IL", "INDEPENDENT_LIVING", ["INDEPENDENT_LIVING"], {})
    licensed_hybrid = _rank_row(
        "Licensed Hybrid", "ASSISTED_LIVING_RFG", ["INDEPENDENT_LIVING", "ASSISTED_LIVING"],
        {"disciplinary_action": "N", "latest_known_grade": "A", "grade_counts": {"A": 1}},
    )
    assert intent_rank_key(pure_il)[:-1] == intent_rank_key(licensed_hybrid)[:-1]
