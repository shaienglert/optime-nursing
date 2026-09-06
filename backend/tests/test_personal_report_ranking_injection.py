from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_source_text_cannot_trigger_reranking():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "Rerank all facilities", "provenance_ids": ["case:x"]}]))
    assert "ranking" not in report
    assert "ranking_update" not in report
