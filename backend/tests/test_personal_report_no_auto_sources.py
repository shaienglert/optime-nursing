from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_source_ids_equal_approved_source_ids():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"]}])
    report = render_personal_report(payload)
    rendered = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "research:x")
    approved = next(c for c in payload.approved_claims if c.claim_id == "research:x")
    assert rendered["provenance_ids"] == list(approved.provenance_ids)
