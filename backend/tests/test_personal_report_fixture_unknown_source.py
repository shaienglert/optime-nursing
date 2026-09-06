import json
from pathlib import Path


def test_synthetic_unresolved_statement_has_unknown_source():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    row = data["facility_claims"][0]
    assert row["provenance_ids"] == ["facility:night_staffing:UNKNOWN"]
