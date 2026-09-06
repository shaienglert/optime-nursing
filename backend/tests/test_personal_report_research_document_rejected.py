from app.services.personal_decision_report_builder import build_personal_report_payload


def test_document_only_research_claim_is_dropped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:doc", "approved_text": "Document finding.", "provenance_ids": ["document:1"]}])
    assert "research:doc" not in {c.claim_id for c in payload.approved_claims}
