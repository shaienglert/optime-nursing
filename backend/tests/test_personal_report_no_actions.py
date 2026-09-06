from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_contains_no_actions_or_tool_calls():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert not set(report).intersection({"actions", "tools", "tool_calls", "commands", "tasks"})
