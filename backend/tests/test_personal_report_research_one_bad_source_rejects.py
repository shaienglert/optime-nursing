from app.services.personal_decision_report_builder import build_personal_report_payload


def test_one_external_source_rejects_entire_research_claim():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:multi", "approved_text": "Finding.", "provenance_ids": ["research:RI-1", "web:2"]}])
    assert "research:multi" not in {c.claim_id for c in payload.approved_claims}
