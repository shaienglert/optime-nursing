from app.services.personal_decision_report_renderer import SECTION_TITLES


def test_report_section_order_is_fixed_and_closed():
    assert list(SECTION_TITLES) == [
        "YOUR_SITUATION", "YOUR_ROLE", "WHAT_MATTERS", "WHY_RECOMMENDATION",
        "WHY_THIS_PLACE", "SUCCESSFUL_TRANSITION", "BEFORE_YOU_DECIDE",
    ]
