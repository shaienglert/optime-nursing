import json
from pathlib import Path


def test_expected_role_is_in_role_section():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    section = next(s for s in data["sections"] if any(c["claim_id"] == "case:role" for c in s["claims"]))
    assert section["section"] == "YOUR_ROLE"
