import json
from pathlib import Path
from app.services.personal_decision_report_renderer import SECTION_TITLES


def test_every_expected_title_is_static_map_value():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(s["title"] == SECTION_TITLES[s["section"]] for s in data["sections"])
