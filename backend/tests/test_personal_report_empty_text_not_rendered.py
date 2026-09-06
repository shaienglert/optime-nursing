from app.services.personal_decision_report_builder import build_personal_report_payload


def test_empty_research_text_is_not_rendered():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:empty", "approved_text": "   ", "provenance_ids": ["research:RI-1"]}])
    assert "research:empty" not in {c.claim_id for c in payload.approved_claims}
