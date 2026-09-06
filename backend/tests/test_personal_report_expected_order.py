import json
from pathlib import Path


def test_synthetic_expected_section_order_is_fixed():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert [s["section"] for s in data["sections"]] == ["YOUR_ROLE", "WHAT_MATTERS", "WHY_RECOMMENDATION", "SUCCESSFUL_TRANSITION", "BEFORE_YOU_DECIDE"]
