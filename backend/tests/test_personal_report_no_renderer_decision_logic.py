import inspect

from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_only_projects_canonical_decision_fields():
    source = inspect.getsource(render_personal_report)
    assert "derive_canonical_decision_state" not in source
    assert "score" not in source.lower()
    assert "rank" not in source.lower()
