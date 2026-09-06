import json
from pathlib import Path


def test_synthetic_fixture_has_exactly_four_external_approved_claims():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert len(data["case_claims"]) + len(data["research_claims"]) + len(data["facility_claims"]) == 4
