import json
from pathlib import Path


def test_expected_runtime_portion_has_runtime_top_level_shape():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    runtime = {k: v for k, v in data.items() if k not in {"fixture_only", "warning"}}
    assert set(runtime) == {"report_type", "report_version", "decision", "sections"}
