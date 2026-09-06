from app.services.personal_decision_report_builder import build_personal_report_payload


def test_provenance_is_not_turned_into_narrative_text():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "provenance_ids": ["research:RI-1"]}])
    assert "research:x" not in {c.claim_id for c in payload.approved_claims}
