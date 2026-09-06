from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_phase_is_direct_canonical_projection():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    report = render_personal_report(payload)
    assert report["decision"]["phase"] == payload.canonical_decision["phase"]
