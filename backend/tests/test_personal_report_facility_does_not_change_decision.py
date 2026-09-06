from app.services.personal_decision_report_builder import build_personal_report_payload


def test_report_facility_claims_do_not_change_decision_state():
    result = {"results": [], "decision_intelligence": {}}
    baseline = build_personal_report_payload(result)
    with_fact = build_personal_report_payload(result, facility_claims=[{"claim_id": "facility:x", "text": "Verified fact.", "verified": True, "provenance_ids": ["facility:registry:x"]}])
    assert baseline.canonical_decision == with_fact.canonical_decision
