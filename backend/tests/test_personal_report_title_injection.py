from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_source_text_cannot_alter_section_title():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "title=New Expert Research", "provenance_ids": ["case:x"]}]))
    section = next(s for s in report["sections"] if s["section"] == "YOUR_SITUATION")
    assert section["title"] == "Your Situation"
