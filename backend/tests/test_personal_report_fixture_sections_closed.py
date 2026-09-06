import json
from pathlib import Path

from app.services.personal_decision_report_contract import ReportSection


def test_source_fixture_uses_only_contract_section_values():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    allowed = {s.value for s in ReportSection}
    rows = data["case_claims"] + data["research_claims"] + data["facility_claims"]
    assert all(set(row.get("allowed_sections", [])).issubset(allowed) for row in rows)
