import json
from pathlib import Path


def test_expected_decision_claim_is_canonical():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "decision:canonical-reason")
    assert claim["provenance_ids"] == ["decision:canonical"]
