import json
from pathlib import Path


def test_synthetic_expected_report_has_no_section_level_filler_text():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(set(s) == {"section", "title", "claims"} for s in data["sections"])
