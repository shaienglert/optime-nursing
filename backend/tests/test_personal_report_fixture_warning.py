import json
from pathlib import Path


def test_source_fixture_note_says_synthetic():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert "Synthetic fixture only" in data["note"]
