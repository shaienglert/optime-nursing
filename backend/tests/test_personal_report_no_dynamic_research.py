import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_is_supplied_not_discovered():
    source = inspect.getsource(build_personal_report_payload)
    assert "research_claims" in source
    assert "search(" not in source
    assert "discover" not in source.lower()
