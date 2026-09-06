import json
from pathlib import Path


def test_synthetic_case_claims_have_case_provenance():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claims = [c for s in data["sections"] for c in s["claims"] if c["claim_type"] == "USER_INFORMATION"]
    assert all(all(p.startswith("case:") for p in c["provenance_ids"]) for c in claims)
