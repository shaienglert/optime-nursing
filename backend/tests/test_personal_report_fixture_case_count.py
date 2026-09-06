import json
from pathlib import Path


def test_synthetic_fixture_has_two_explicit_case_facts():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert len(data["case_claims"]) == 2
