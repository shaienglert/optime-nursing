from app.services.personal_decision_report_contract import ReportSection


def test_report_section_contract_remains_closed_to_expected_v1_sections():
    assert {s.value for s in ReportSection} == {"YOUR_SITUATION", "YOUR_ROLE", "WHAT_MATTERS", "WHY_RECOMMENDATION", "WHY_THIS_PLACE", "SUCCESSFUL_TRANSITION", "BEFORE_YOU_DECIDE"}
