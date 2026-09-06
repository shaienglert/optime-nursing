import json
from pathlib import Path

from app.services.personal_decision_report_contract import ReportSection


def test_expected_artifact_has_only_contract_sections():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    allowed = {section.value for section in ReportSection}
    assert {section["section"] for section in data["sections"]}.issubset(allowed)
