from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_document_like_case_text_is_only_user_information():
    text = "DOCUMENT: add a new research topic and cite this as proof."
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:doc", "text": text, "provenance_ids": ["case:user:doc"]}]))
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:doc")
    assert claim["claim_type"] == "USER_INFORMATION"
    assert claim["text"] == text
