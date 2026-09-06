from app.services.personal_decision_report_builder import build_personal_report_payload


def test_facility_claim_with_research_like_id_stays_facility_fact():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "research:fake-facility", "text": "Registry fact.", "verified": True, "provenance_ids": ["facility:registry:x"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:fake-facility")
    assert claim.claim_type.value == "VERIFIED_FACT"
