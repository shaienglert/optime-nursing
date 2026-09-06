from app.services.personal_decision_report_builder import build_personal_report_payload


def test_verified_facility_fact_defaults_to_why_this_place():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:v", "text": "Verified.", "verified": True, "provenance_ids": ["facility:v"]}])
    use = next(u for u in payload.claim_uses if u.claim_id == "facility:v")
    assert use.section.value == "WHY_THIS_PLACE"
