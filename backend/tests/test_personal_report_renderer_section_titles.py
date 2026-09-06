from app.services.personal_decision_report_renderer import SECTION_TITLES


def test_section_titles_are_static_not_ai_generated():
    assert SECTION_TITLES["WHY_RECOMMENDATION"] == "Why This Recommendation"
    assert SECTION_TITLES["BEFORE_YOU_DECIDE"] == "What We Still Don't Know"
