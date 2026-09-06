from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_contains_no_expert_or_research_agenda_creation_fields():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert not set(report).intersection({"experts", "new_experts", "research_agenda", "new_domains", "research_topics"})
