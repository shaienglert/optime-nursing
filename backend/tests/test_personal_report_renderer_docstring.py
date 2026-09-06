from app.services import personal_decision_report_renderer


def test_renderer_module_documents_no_llm():
    assert "No LLM is used" in (personal_decision_report_renderer.__doc__ or "")
