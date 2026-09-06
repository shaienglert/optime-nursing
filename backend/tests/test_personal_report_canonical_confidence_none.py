from app.services.personal_decision_report_builder import build_personal_report_payload


def test_canonical_reason_has_no_report_generated_confidence():
    claim = build_personal_report_payload({"results": [], "decision_intelligence": {}}).approved_claims[0]
    assert claim.confidence is None
