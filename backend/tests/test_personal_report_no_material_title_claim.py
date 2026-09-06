from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_static_titles_have_no_claim_id_or_provenance_semantics():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    section = report["sections"][0]
    assert isinstance(section["title"], str)
    assert "title_claim_id" not in section
