import inspect

from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_receives_only_governed_payload_not_raw_sources():
    params = list(inspect.signature(render_personal_report).parameters)
    assert params == ["payload"]
