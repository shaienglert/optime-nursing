import json
from pathlib import Path


def test_expected_artifact_sections_are_all_materially_populated():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(section["claims"] for section in data["sections"])
