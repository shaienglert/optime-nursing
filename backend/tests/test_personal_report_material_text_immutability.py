from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_never_rewrites_material_text():
    exact = "Family reports this exact statement; it must not be improved."
    report = render_personal_report(build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:exact", "text": exact, "provenance_ids": ["case:exact"]}],
    ))
    rendered = next(c["text"] for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:exact")
    assert rendered == exact
