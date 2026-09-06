from app.services.personal_decision_report_builder import build_personal_report_payload


def test_claim_id_is_not_treated_as_provenance():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:RI-1", "approved_text": "Finding.", "provenance_ids": []}])
    assert "research:RI-1" not in {c.claim_id for c in payload.approved_claims}
