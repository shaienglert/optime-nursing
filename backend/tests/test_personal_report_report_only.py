import copy

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_report_is_projection_not_mutation():
    result = {"results": [], "decision_intelligence": {}}
    original = copy.deepcopy(result)
    build_personal_report_payload(result, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"]}])
    assert result == original
