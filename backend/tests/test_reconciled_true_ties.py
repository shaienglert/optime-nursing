from app.services.client_intent_runtime import intent_rank_key
from app.services.decision_engine_evidence import _result_sort_key
from app.services.patient_decision_engine_runtime import _reassign_rank_metadata


def _row(name):
    return {"facility_name":name,"canonical_facility_id":name,"canonical_type":"INDEPENDENT_LIVING","eligibility_status":"ELIGIBLE","care_setting_fit":{"status":"PRIMARY_FIT"},"patient_match_score":1.0,"client_intent_fit":{"hard_gate":"PASS","nice_match":[],"nice_mismatch":[],"nice_fit_scores":{},"public_reputation":{},"relevant_evidence_known_count":0,"relevant_evidence_unknown_count":0}}


def test_names_do_not_break_true_ties():
    assert intent_rank_key(_row("Alpha")) == intent_rank_key(_row("Zulu"))
    assert _result_sort_key(_row("Alpha")) == _result_sort_key(_row("Zulu"))


def test_late_rank_metadata_preserves_true_tie():
    rows=[_row("Alpha"),_row("Zulu")]
    _reassign_rank_metadata(rows)
    assert [r["rank_position"] for r in rows] == [1,1]
    assert all(r["rank_tie_status"] == "JOINT_RANK" for r in rows)
