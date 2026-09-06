import json
from pathlib import Path


def test_synthetic_artifact_warning_is_explicit():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["warning"] == "Synthetic example. Not a real client or facility report."
