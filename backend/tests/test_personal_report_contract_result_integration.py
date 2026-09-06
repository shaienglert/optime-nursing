from app.services.personal_decision_report_builder import build_personal_report_payload


def test_valid_closed_world_payload_is_returned():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "X.", "provenance_ids": ["research:RI-X"]}])
    assert any(c.claim_id == "research:x" for c in payload.approved_claims)
