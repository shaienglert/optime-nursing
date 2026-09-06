import json
from pathlib import Path


def test_expected_report_shape_is_minimal_closed_world():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert set(data) == {"report_type", "report_version", "decision", "sections", "fixture_only", "warning"}
