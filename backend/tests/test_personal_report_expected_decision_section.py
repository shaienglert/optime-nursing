import json
from pathlib import Path


def test_expected_decision_reason_is_in_why_recommendation():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    section = next(s for s in data["sections"] if any(c["claim_id"] == "decision:canonical-reason" for c in s["claims"]))
    assert section["section"] == "WHY_RECOMMENDATION"
