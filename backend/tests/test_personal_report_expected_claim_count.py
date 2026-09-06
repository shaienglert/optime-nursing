import json
from pathlib import Path


def test_synthetic_expected_report_has_four_inputs_plus_canonical_claim():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert sum(len(s["claims"]) for s in data["sections"]) == 5
