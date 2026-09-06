import json
from pathlib import Path


def test_source_fixture_research_is_institute_namespaced():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
    assert all(all(p.startswith("research:") for p in row["provenance_ids"]) for row in data["research_claims"])
