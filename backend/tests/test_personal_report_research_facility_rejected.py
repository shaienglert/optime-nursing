from app.services.personal_decision_report_builder import build_personal_report_payload


def test_facility_only_research_claim_is_dropped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:facility", "approved_text": "Facility-derived theory.", "provenance_ids": ["facility:x"]}])
    assert "research:facility" not in {c.claim_id for c in payload.approved_claims}
