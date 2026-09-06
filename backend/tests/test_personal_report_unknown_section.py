from app.services.personal_decision_report_builder import build_personal_report_payload


def test_unknown_defaults_to_before_you_decide():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:u", "text": "Not verified.", "unknown": True, "provenance_ids": ["facility:u:UNKNOWN"]}])
    use = next(u for u in payload.claim_uses if u.claim_id == "facility:u")
    assert use.section.value == "BEFORE_YOU_DECIDE"
