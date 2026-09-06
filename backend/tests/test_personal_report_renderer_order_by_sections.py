from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_uses_fixed_section_order():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[
        {"claim_id": "case:role", "text": "Role.", "provenance_ids": ["case:role"], "allowed_sections": ["YOUR_ROLE"]},
        {"claim_id": "case:situation", "text": "Situation.", "provenance_ids": ["case:situation"], "allowed_sections": ["YOUR_SITUATION"]},
    ]))
    order = [s["section"] for s in report["sections"]]
    assert order.index("YOUR_SITUATION") < order.index("YOUR_ROLE") < order.index("WHY_RECOMMENDATION")
