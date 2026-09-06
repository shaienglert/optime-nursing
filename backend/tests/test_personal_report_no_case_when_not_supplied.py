from app.services.personal_decision_report_builder import build_personal_report_payload


def test_no_supplied_case_evidence_means_no_user_information_claims():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert not any(c.claim_type.value == "USER_INFORMATION" for c in payload.approved_claims)
