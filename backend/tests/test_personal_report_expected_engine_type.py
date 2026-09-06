import json
from pathlib import Path


def test_synthetic_canonical_reason_is_engine_conclusion_type():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "decision:canonical-reason")
    assert claim["claim_type"] == "ENGINE_CONCLUSION"
