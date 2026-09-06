import json
from pathlib import Path


def test_synthetic_case_facts_are_user_information_type():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claims = [c for s in data["sections"] for c in s["claims"] if c["claim_id"].startswith("case:")]
    assert all(c["claim_type"] == "USER_INFORMATION" for c in claims)
