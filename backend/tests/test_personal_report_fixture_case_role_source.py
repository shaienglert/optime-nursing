import json
from pathlib import Path


def test_synthetic_role_statement_is_user_sourced():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    row = next(r for r in data["case_claims"] if r["claim_id"] == "case:role")
    assert row["provenance_ids"] == ["case:user_input:role"]
