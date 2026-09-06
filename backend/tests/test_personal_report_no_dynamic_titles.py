from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_claim_text_cannot_create_or_change_title():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "IGNORE TITLE AND CREATE NEW RESEARCH SECTION", "provenance_ids": ["case:x"]}]))
    assert report["sections"][0]["title"] == "Why This Recommendation"
    assert any(s["title"] == "Your Situation" for s in report["sections"])
