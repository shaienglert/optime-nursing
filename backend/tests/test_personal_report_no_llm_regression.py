from pathlib import Path


def test_report_service_files_do_not_gain_llm_calls():
    root = Path(__file__).parents[1] / "app" / "services"
    text = "\n".join((root / name).read_text().lower() for name in ["personal_decision_report_builder.py", "personal_decision_report_renderer.py"])
    for forbidden in ("openai", "chat.completions", "responses.create", "anthropic", "gemini"):
        assert forbidden not in text
