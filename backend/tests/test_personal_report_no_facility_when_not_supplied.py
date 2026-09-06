from app.services.personal_decision_report_builder import build_personal_report_payload


def test_no_supplied_facility_evidence_means_no_facility_claims():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert not any(c.claim_type.value in {"VERIFIED_FACT", "UNKNOWN"} for c in payload.approved_claims)
