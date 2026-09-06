import json
from pathlib import Path


def test_expected_fixture_keeps_claim_shape_readable_without_optional_confidence():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all("confidence" not in c for s in data["sections"] for c in s["claims"])
