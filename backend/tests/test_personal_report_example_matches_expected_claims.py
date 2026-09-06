import json
from pathlib import Path


def test_example_and_expected_fixture_claim_ids_match():
    root = Path(__file__).parent / "fixtures"
    source = json.loads((root / "personal_report_example.json").read_text())
    expected = json.loads((root / "personal_report_expected.json").read_text())
    source_ids = {r["claim_id"] for group in (source["case_claims"], source["research_claims"], source["facility_claims"]) for r in group}
    expected_ids = {c["claim_id"] for s in expected["sections"] for c in s["claims"]} - {"decision:canonical-reason"}
    assert source_ids == expected_ids
