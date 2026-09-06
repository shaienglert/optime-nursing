from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_decision_surface_has_no_ranking_mutation_fields():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert set(report["decision"]) == {"phase", "finality", "can_show_recommendations"}
