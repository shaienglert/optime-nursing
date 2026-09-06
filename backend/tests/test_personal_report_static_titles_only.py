from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import SECTION_TITLES, render_personal_report


def test_every_runtime_title_is_static_map_value():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert all(s["title"] == SECTION_TITLES[s["section"]] for s in report["sections"])
