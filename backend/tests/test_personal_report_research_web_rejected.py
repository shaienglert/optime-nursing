from app.services.personal_decision_report_builder import build_personal_report_payload


def test_web_only_research_claim_is_dropped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:web", "approved_text": "Web finding.", "provenance_ids": ["web:1"]}])
    assert "research:web" not in {c.claim_id for c in payload.approved_claims}
