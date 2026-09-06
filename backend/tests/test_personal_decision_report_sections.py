import pytest

from app.services.personal_decision_report_contract import ReportSection
from app.services.personal_decision_report_sections import normalize_report_sections


def test_string_section_is_normalized_to_closed_enum():
    assert normalize_report_sections(["YOUR_ROLE"], ReportSection.YOUR_SITUATION) == (ReportSection.YOUR_ROLE,)


def test_unknown_section_is_rejected_not_invented():
    with pytest.raises(ValueError):
        normalize_report_sections(["AI_INVENTED_SECTION"], ReportSection.YOUR_SITUATION)
