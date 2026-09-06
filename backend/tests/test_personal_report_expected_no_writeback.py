import json
from pathlib import Path


def test_expected_artifact_has_no_writeback_or_research_request():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert not set(data).intersection({"writeback", "decision_update", "ranking_update", "research_request"})
