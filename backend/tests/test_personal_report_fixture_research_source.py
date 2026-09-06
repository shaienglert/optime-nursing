import json
from pathlib import Path


def test_synthetic_transition_statement_is_institute_sourced():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    row = data["research_claims"][0]
    assert row["provenance_ids"] == ["research:RI-TRANSITION-AUTONOMY"]
