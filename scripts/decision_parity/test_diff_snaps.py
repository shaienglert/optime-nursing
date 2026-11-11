"""Parity must distinguish recommendation order from unordered disposition records."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diff_snaps import walk


def _diff(a, b, path="$.http_recommendations.body.care_setting_policy.decision_intelligence.facility_selection_pipeline.candidate_dispositions"):
    output = []
    walk(a, b, path, output)
    return output


def test_unordered_dispositions_compare_by_facility_identity():
    left = [{"canonical_facility_id": "NV-A", "reason_code": "MUST_PASS"},
            {"canonical_facility_id": "NV-B", "reason_code": "MUST_PENDING"}]
    assert _diff(left, list(reversed(left))) == []


def test_disposition_status_change_is_still_rejected():
    left = [{"canonical_facility_id": "NV-A", "reason_code": "MUST_PASS"}]
    right = [{"canonical_facility_id": "NV-A", "reason_code": "MUST_FAIL"}]
    differences = _diff(left, right)
    assert len(differences) == 1
    assert "reason_code" in differences[0][0]


def test_missing_or_added_candidate_is_still_rejected():
    left = [{"canonical_facility_id": "NV-A", "reason_code": "MUST_PASS"}]
    right = left + [{"canonical_facility_id": "NV-B", "reason_code": "MUST_PASS"}]
    differences = _diff(left, right)
    assert len(differences) == 1 and differences[0][1] == "added"


def test_ordered_recommendations_still_fail_when_swapped():
    left = [{"canonical_facility_id": "NV-A"}, {"canonical_facility_id": "NV-B"}]
    differences = _diff(left, list(reversed(left)), path="$.http_recommendations.body.results")
    assert differences


def test_unordered_pending_evidence_list_requires_identical_facility_data():
    path = "$.run_limit5.must_pending_verification_candidates"
    left = [{"canonical_facility_id": "NV-A", "must_unknown": ["SECURED_UNIT_AVAILABLE"]},
            {"canonical_facility_id": "NV-B", "must_unknown": ["TRANSPORTATION"]}]
    assert _diff(left, list(reversed(left)), path=path) == []
    changed = [dict(left[1]), dict(left[0])]
    changed[0]["must_unknown"] = []
    diffs = _diff(left, changed, path=path)
    assert len(diffs) == 1
    assert "NV-B" in diffs[0][0]
