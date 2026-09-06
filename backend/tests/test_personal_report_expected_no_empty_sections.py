import json
from pathlib import Path


def test_synthetic_expected_report_contains_no_empty_sections():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(s["claims"] for s in data["sections"])
