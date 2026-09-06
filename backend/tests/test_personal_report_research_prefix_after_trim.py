from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_provenance_with_external_namespace_is_rejected():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "X.", "provenance_ids": [" external:research:RI-X "]}])
    assert "research:x" not in {c.claim_id for c in payload.approved_claims}
