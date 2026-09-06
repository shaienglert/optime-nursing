import json
from pathlib import Path
from app.services.personal_decision_report_contract import ReportSection


def test_synthetic_expected_sections_are_contract_known():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    allowed = {s.value for s in ReportSection}
    assert all(s["section"] in allowed for s in data["sections"])
