import json
from pathlib import Path


def test_synthetic_expected_report_can_show_is_true_only_for_final_fixture():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert data["decision"]["phase"] == "FINAL_RECOMMENDATION"
    assert data["decision"]["can_show_recommendations"] is True
