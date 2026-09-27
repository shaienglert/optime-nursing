from app.services.client_intent_runtime import intent_rank_key
from app.services.decision_engine_evidence import _result_sort_key


def _row(name):
    return {
        "facility_name": name,
        "canonical_facility_id": name,
        "canonical_type": "INDEPENDENT_LIVING",
        "eligibility_status": "ELIGIBLE",
        "care_setting_fit": {"status": "PRIMARY_FIT"},
        "patient_match_score": 1.0,
        "client_intent_fit": {
            "hard_gate": "PASS", "nice_match": [], "nice_mismatch": [],
            "nice_fit_scores": {}, "public_reputation": {},
            "relevant_evidence_known_count": 0, "relevant_evidence_unknown_count": 0,
        },
    }


def test_names_do_not_break_true_intent_tie():
    assert intent_rank_key(_row("Alpha")) == intent_rank_key(_row("Zulu"))


def test_names_do_not_break_true_governed_result_tie():
    assert _result_sort_key(_row("Alpha")) == _result_sort_key(_row("Zulu"))
