import inspect

from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_has_no_decision_computation_calls():
    source = inspect.getsource(render_personal_report).lower()
    assert "derive_canonical" not in source
    assert "decide(" not in source
    assert "recommend(" not in source
