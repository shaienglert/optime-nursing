import json
from pathlib import Path


def test_expected_artifact_is_closed_world_v1():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["report_version"] == "v1-closed-world"
