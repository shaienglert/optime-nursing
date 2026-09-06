import json
from pathlib import Path


def test_example_artifact_is_explicitly_synthetic():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["fixture_only"] is True
    assert "Not a real client" in data["warning"]
