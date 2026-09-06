import json
from pathlib import Path


def test_expected_provenance_namespaces_match_claim_classes():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claims = [c for s in data["sections"] for c in s["claims"]]
    for claim in claims:
        if claim["claim_type"] == "RESEARCH_FINDING":
            assert all(p.startswith("research:") for p in claim["provenance_ids"])
        if claim["claim_type"] == "ENGINE_CONCLUSION":
            assert all(p.startswith("decision:") for p in claim["provenance_ids"])
