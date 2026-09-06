import inspect

from app.services import personal_decision_report_builder, personal_decision_report_renderer


def test_report_pipeline_contains_no_llm_web_or_research_calls():
    source = inspect.getsource(personal_decision_report_builder) + inspect.getsource(personal_decision_report_renderer)
    forbidden = ["openai", "requests.", "httpx.", "web_search", "research_service", "chat.completions", "responses.create"]
    lowered = source.lower()
    assert all(token.lower() not in lowered for token in forbidden)
