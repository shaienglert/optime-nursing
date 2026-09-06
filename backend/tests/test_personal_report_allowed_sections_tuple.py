from app.services.personal_decision_report_builder import build_personal_report_payload


def test_allowed_sections_are_tuple():
    claim = build_personal_report_payload({"results": [], "decision_intelligence": {}}).approved_claims[0]
    assert isinstance(claim.allowed_sections, tuple)
