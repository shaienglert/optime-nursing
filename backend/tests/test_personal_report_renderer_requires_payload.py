import inspect

from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_has_single_governed_payload_input():
    assert list(inspect.signature(render_personal_report).parameters) == ["payload"]
