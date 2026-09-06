import json
from pathlib import Path


def test_expected_report_has_no_situation_section_without_situation_claim():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert "YOUR_SITUATION" not in {s["section"] for s in data["sections"]}
