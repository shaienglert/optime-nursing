import inspect

from app.services import personal_decision_report_builder, personal_decision_report_renderer


def test_report_modules_import_no_network_client():
    source = inspect.getsource(personal_decision_report_builder) + inspect.getsource(personal_decision_report_renderer)
    lowered = source.lower()
    assert "import requests" not in lowered
    assert "import httpx" not in lowered
