from app.services.personal_decision_report_builder import build_personal_report_payload


def test_claim_uses_are_tuple():
    assert isinstance(build_personal_report_payload({"results": [], "decision_intelligence": {}}).claim_uses, tuple)
