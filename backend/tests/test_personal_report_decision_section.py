from app.services.personal_decision_report_builder import build_personal_report_payload


def test_canonical_reason_is_fixed_to_why_recommendation():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    use = next(u for u in payload.claim_uses if u.claim_id == "decision:canonical-reason")
    assert use.section.value == "WHY_RECOMMENDATION"
