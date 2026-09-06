from app.services.personal_decision_report_builder import build_personal_report_payload


def test_case_only_research_claim_is_dropped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:case", "approved_text": "Case-derived theory.", "provenance_ids": ["case:user:x"]}])
    assert "research:case" not in {c.claim_id for c in payload.approved_claims}
