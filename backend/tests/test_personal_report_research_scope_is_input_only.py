import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_has_no_research_agenda_or_expert_creation_logic():
    source = inspect.getsource(build_personal_report_payload).lower()
    assert "research_agenda" not in source
    assert "create_expert" not in source
    assert "new_domain" not in source
