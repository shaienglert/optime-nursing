from app.services.personal_decision_report_builder import build_personal_report_payload


def test_facility_input_cannot_self_override_unknown_taxonomy():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:x", "text": "Unresolved.", "unknown": True, "provenance_ids": ["facility:x:UNKNOWN"], "claim_type": "VERIFIED_FACT"}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "facility:x")
    assert claim.claim_type.value == "UNKNOWN"
