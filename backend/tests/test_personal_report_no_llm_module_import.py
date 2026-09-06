import inspect

from app.services import personal_decision_report_builder, personal_decision_report_renderer


def test_report_modules_import_no_ai_client():
    source = inspect.getsource(personal_decision_report_builder) + inspect.getsource(personal_decision_report_renderer)
    assert "from openai" not in source.lower()
    assert "import openai" not in source.lower()
