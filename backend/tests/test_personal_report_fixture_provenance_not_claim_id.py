import json
from pathlib import Path


def test_fixture_claim_ids_and_provenance_are_separate_fields():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    assert all("claim_id" in c and "provenance_ids" in c for s in data["sections"] for c in s["claims"])
