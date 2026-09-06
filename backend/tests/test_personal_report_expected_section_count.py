import json
from pathlib import Path


def test_synthetic_expected_report_has_only_populated_sections():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert len(data["sections"]) == 5
