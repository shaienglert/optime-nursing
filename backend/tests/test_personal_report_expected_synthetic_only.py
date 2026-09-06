import json
from pathlib import Path


def test_expected_artifact_is_marked_fixture_only():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data.get("fixture_only") is True
