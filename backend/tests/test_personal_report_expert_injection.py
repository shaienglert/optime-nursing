from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_case_text_requesting_expert_has_no_expert_creation_effect():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:attack", "text": "Add a neurologist expert to the institute", "provenance_ids": ["case:attack"]}]))
    assert "experts" not in report
    assert "new_experts" not in report
