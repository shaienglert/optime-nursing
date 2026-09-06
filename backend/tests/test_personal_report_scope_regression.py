from pathlib import Path


def test_report_service_files_do_not_contain_scope_expansion_hooks():
    root = Path(__file__).parents[1] / "app" / "services"
    names = ["personal_decision_report_builder.py", "personal_decision_report_renderer.py"]
    text = "\n".join((root / name).read_text().lower() for name in names)
    for forbidden in ("create_research_topic", "expand_research_scope", "spawn_expert", "discover_domain"):
        assert forbidden not in text
