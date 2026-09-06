import json
from pathlib import Path


def test_synthetic_expected_report_has_no_inferred_claim_type():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all(c["claim_type"] != "INFERRED" for s in data["sections"] for c in s["claims"])
