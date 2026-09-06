import json
from pathlib import Path

from app.services.personal_decision_report_renderer import SECTION_TITLES


def test_expected_titles_are_renderer_constants():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(section["title"] == SECTION_TITLES[section["section"]] for section in data["sections"])
