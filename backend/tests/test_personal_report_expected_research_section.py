import json
from pathlib import Path


def test_expected_research_is_in_transition_section():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    section = next(s for s in data["sections"] if any(c["claim_id"] == "research:transition-autonomy" for c in s["claims"]))
    assert section["section"] == "SUCCESSFUL_TRANSITION"
