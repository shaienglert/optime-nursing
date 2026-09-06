import json
from pathlib import Path


def test_synthetic_expected_report_contains_no_research_scope_expansion():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text().lower()
    assert '"new_domains"' not in text
    assert '"research_agenda"' not in text
    assert '"new_experts"' not in text
