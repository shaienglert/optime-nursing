from app.services.personal_decision_report_renderer import SECTION_TITLES


def test_section_title_map_has_exact_v1_keys():
    assert tuple(SECTION_TITLES) == ("YOUR_SITUATION", "YOUR_ROLE", "WHAT_MATTERS", "WHY_RECOMMENDATION", "WHY_THIS_PLACE", "SUCCESSFUL_TRANSITION", "BEFORE_YOU_DECIDE")
