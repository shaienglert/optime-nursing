import json
from pathlib import Path


def test_expected_fixture_material_claims_all_have_provenance():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claims = [claim for section in data["sections"] for claim in section["claims"]]
    assert claims
    assert all(claim["provenance_ids"] for claim in claims)
