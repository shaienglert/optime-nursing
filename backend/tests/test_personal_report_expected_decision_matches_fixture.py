import json
from pathlib import Path


def test_expected_artifact_decision_is_final_fixture_state():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["decision"] == {"phase": "FINAL_RECOMMENDATION", "finality": "FINAL", "can_show_recommendations": True}
