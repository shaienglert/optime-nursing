import copy

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_does_not_mutate_claim_inputs():
    case = [{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:x"]}]
    research = [{"claim_id": "research:x", "approved_text": "R.", "provenance_ids": ["research:RI-X"]}]
    facility = [{"claim_id": "facility:x", "text": "F.", "verified": True, "provenance_ids": ["facility:x"]}]
    before = copy.deepcopy((case, research, facility))
    build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=case, research_claims=research, facility_claims=facility)
    assert (case, research, facility) == before
