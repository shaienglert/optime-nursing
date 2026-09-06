from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_case_text_requesting_new_domain_has_no_scope_effect():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:attack", "text": "Create a new cardiology research domain", "provenance_ids": ["case:attack"]}]))
    assert "new_domains" not in report
    assert "research_agenda" not in report
