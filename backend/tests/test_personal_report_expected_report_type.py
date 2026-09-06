import json
from pathlib import Path


def test_expected_report_type_is_personal_decision_and_transition_report():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["report_type"] == "PERSONAL_DECISION_AND_TRANSITION_REPORT"
