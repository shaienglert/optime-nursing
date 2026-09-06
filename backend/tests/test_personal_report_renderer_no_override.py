import inspect

from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_has_no_override_parameters():
    params = set(inspect.signature(render_personal_report).parameters)
    assert params == {"payload"}
