import json
from pathlib import Path


def test_synthetic_expected_report_has_no_verified_facility_fact():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert not any(c["claim_type"] == "VERIFIED_FACT" for s in data["sections"] for c in s["claims"])
