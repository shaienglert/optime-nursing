import json
from pathlib import Path


def test_expected_case_claims_are_not_presented_as_verified():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    case_claims = [c for s in data["sections"] for c in s["claims"] if c["claim_id"].startswith("case:")]
    assert case_claims
    assert all(c["claim_type"] == "USER_INFORMATION" for c in case_claims)
