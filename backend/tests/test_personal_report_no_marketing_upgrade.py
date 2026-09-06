from app.services.personal_decision_report_builder import build_personal_report_payload


def test_unverified_marketing_claim_is_dropped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:marketing", "text": "Best care in town.", "verified": False, "provenance_ids": ["facility:marketing"]}])
    assert "facility:marketing" not in {c.claim_id for c in payload.approved_claims}
