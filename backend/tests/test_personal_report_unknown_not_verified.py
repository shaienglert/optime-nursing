from app.services.personal_decision_report_builder import build_personal_report_payload


def test_unknown_claim_never_becomes_verified_fact():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:u", "text": "Unresolved.", "unknown": True, "verified": True, "provenance_ids": ["facility:u:UNKNOWN"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "facility:u")
    assert claim.claim_type.value == "UNKNOWN"
