import json
from pathlib import Path


def test_synthetic_fixture_has_one_preapproved_research_finding():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert len(data["research_claims"]) == 1
