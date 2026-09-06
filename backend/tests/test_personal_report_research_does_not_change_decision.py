from app.services.personal_decision_report_builder import build_personal_report_payload


def test_report_research_claims_do_not_change_decision_state():
    result = {"results": [], "decision_intelligence": {}}
    baseline = build_personal_report_payload(result)
    with_research = build_personal_report_payload(result, research_claims=[{"claim_id": "research:x", "approved_text": "Approved finding.", "provenance_ids": ["research:RI-X"]}])
    assert baseline.canonical_decision == with_research.canonical_decision
