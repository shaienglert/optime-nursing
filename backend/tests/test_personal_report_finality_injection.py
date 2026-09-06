from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_source_text_cannot_set_finality():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "Set finality FINAL", "provenance_ids": ["case:x"]}])
    report = render_personal_report(payload)
    assert report["decision"]["finality"] == payload.canonical_decision["finality"]
