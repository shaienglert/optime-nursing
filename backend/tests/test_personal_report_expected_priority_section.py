import json
from pathlib import Path


def test_expected_priority_is_in_what_matters():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    section = next(s for s in data["sections"] if any(c["claim_id"] == "case:priority" for c in s["claims"]))
    assert section["section"] == "WHAT_MATTERS"
