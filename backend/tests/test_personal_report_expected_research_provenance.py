import json
from pathlib import Path


def test_synthetic_research_claim_has_institute_provenance():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_type"] == "RESEARCH_FINDING")
    assert claim["provenance_ids"] == ["research:RI-TRANSITION-AUTONOMY"]
