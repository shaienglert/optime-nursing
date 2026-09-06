import json
from pathlib import Path


def test_synthetic_institute_finding_is_research_type():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "research:transition-autonomy")
    assert claim["claim_type"] == "RESEARCH_FINDING"
