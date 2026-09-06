import json
from pathlib import Path


def test_synthetic_expected_report_exposes_multiple_provenance_classes():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    types = {c["claim_type"] for s in data["sections"] for c in s["claims"]}
    assert {"USER_INFORMATION", "RESEARCH_FINDING", "ENGINE_CONCLUSION", "UNKNOWN"}.issubset(types)
