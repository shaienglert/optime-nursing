import json
from pathlib import Path


def test_source_fixture_unknown_is_explicit_not_inferred():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    row = next(r for r in data["facility_claims"] if r["claim_id"] == "facility:night-staff")
    assert row["unknown"] is True
