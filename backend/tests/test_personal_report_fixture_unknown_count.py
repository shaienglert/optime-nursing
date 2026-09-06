import json
from pathlib import Path


def test_synthetic_fixture_has_one_explicit_unknown():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert len(data["facility_claims"]) == 1 and data["facility_claims"][0]["unknown"] is True
