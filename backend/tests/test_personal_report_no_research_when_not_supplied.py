from app.services.personal_decision_report_builder import build_personal_report_payload


def test_no_supplied_research_means_no_research_claims():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert not any(c.claim_type.value == "RESEARCH_FINDING" for c in payload.approved_claims)
