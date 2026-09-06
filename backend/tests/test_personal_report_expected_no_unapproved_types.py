import json
from pathlib import Path


def test_expected_report_claim_types_are_closed():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    allowed = {"USER_INFORMATION", "VERIFIED_FACT", "RESEARCH_FINDING", "ENGINE_CONCLUSION", "UNKNOWN"}
    assert {c["claim_type"] for s in data["sections"] for c in s["claims"]}.issubset(allowed)
