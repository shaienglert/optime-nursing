import json
from pathlib import Path


def test_synthetic_fixture_does_not_claim_verified_facility_data():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert not any(row.get("verified") is True for row in data["facility_claims"])
