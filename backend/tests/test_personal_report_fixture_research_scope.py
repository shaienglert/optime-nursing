import json
from pathlib import Path


def test_expected_research_claim_uses_only_institute_provenance():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "research:transition-autonomy")
    assert all(source.startswith("research:") for source in claim["provenance_ids"])
