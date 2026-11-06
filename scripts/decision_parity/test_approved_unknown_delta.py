"""Approval is based on proved semantics, never a generic parity ignore."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from approved_unknown_delta import approved_unknown_evidence_delta
from diff_snaps import walk


def _row(fid="NV-1", must="ELIGIBLE", score=82):
    return {
        "canonical_facility_id": fid,
        "eligibility_status": must,
        "must_eligibility": "MUST_ELIGIBLE",
        "match_score": score,
        "rank_position": 1,
        "matched_needs": [{"parameter_id": "transportation"}],
        "client_intent_fit": {"relevant_evidence_known_count": 6},
    }


def _snap(row):
    return {
        "run_limit5": {"results": [row]},
        "run_limit50": {"results": [row]},
        "http_recommendations": {"body": {"results": [row]}},
    }


def _compare(old, new, case="budget_medicaid_pending"):
    diffs = []
    walk(old, new, "$", diffs)
    return diffs, approved_unknown_evidence_delta(case, old, new, diffs)


def test_narrow_unknown_fix_is_acceptable_only_if_rank_unchanged():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        row = prefix["results"][0]
        row["matched_needs"] = []
        row["client_intent_fit"]["relevant_evidence_known_count"] = 5
    diffs, approved = _compare(before, after)
    assert diffs and approved == set(range(len(diffs)))


def test_any_new_must_eligibility_is_rejected():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        prefix["results"][0]["matched_needs"] = []
        prefix["results"][0]["must_eligibility"] = "MUST_REJECTED"
    assert _compare(before, after)[1] == set()


def test_an_extra_change_to_price_or_score_is_rejected():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        prefix["results"][0]["matched_needs"] = []
    after["run_limit5"]["results"][0]["match_score"] = 90
    assert _compare(before, after)[1] == set()


def test_generic_unrelated_case_never_approved():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        prefix["results"][0]["matched_needs"] = []
    assert _compare(before, after, case="henderson_city")[1] == set()


def test_mismatched_candidate_sets_cannot_be_approved():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    after["run_limit5"]["results"][0]["canonical_facility_id"] = "NV-CHANGED"
    assert _compare(before, after)[1] == set()


def test_unknown_contract_composes_with_only_exact_empty_care_partner_additions():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        prefix["results"][0]["matched_needs"] = []
        prefix["results"][0]["client_intent_fit"]["relevant_evidence_known_count"] = 5
    after["http_recommendations"]["body"]["care_partner_options"] = []
    before["db_side_effects"] = {"decision_artifacts": [{"payload_json": {}}]}
    after["db_side_effects"] = {"decision_artifacts": [{"payload_json": {"care_partner_options": []}}]}
    diffs, accepted = _compare(before, after)
    assert len(diffs) == 8
    assert len(accepted) == 6
    assert all(diffs[index][0].endswith(("matched_needs", "relevant_evidence_known_count"))
               for index in accepted)


def test_nonempty_care_partner_addition_is_not_approved_as_unknown():
    from copy import deepcopy
    before = _snap(_row())
    after = deepcopy(before)
    for prefix in (after["run_limit5"], after["run_limit50"], after["http_recommendations"]["body"]):
        prefix["results"][0]["matched_needs"] = []
        prefix["results"][0]["client_intent_fit"]["relevant_evidence_known_count"] = 5
    after["http_recommendations"]["body"]["care_partner_options"] = [{"agency_id": "unsafe"}]
    assert _compare(before, after)[1] == set()
