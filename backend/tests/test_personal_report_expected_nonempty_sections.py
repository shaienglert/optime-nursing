import json
from pathlib import Path


def test_expected_artifact_sections_are_all_materially_populated_except_documented_situation_placeholder():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    empty = [s["section"] for s in data["sections"] if not s["claims"]]
    assert empty == ["YOUR_SITUATION"]
