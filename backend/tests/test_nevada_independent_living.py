from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_nevada_canonical_universe import build  # noqa: E402
from verify_nevada_independent_living import verify  # noqa: E402


def candidate(license_number="A01-1", name="SUNSET SENIOR APARTMENTS", address="1 SUNSET ST"):
    return {
        "license_number": license_number,
        "business_name": name,
        "legal_name": name,
        "license_category": "Apartment House",
        "license_status": "Active",
        "address": address,
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89101",
        "independent_living_classification": "CANDIDATE_NAME_SIGNAL",
    }


def evidence(license_number="A01-1", name="SUNSET SENIOR APARTMENTS", address="1 SUNSET ST", classification="CONFIRMED_PRIMARY"):
    return {
        "policy": {},
        "records": [{
            "business_license_number": license_number,
            "expected_business_name": name,
            "expected_address": address,
            "classification": classification,
            "canonical_type": "INDEPENDENT_LIVING" if classification == "CONFIRMED_PRIMARY" else "UNKNOWN",
            "primary_source_url": "https://example.invalid/property",
            "evidence_summary": "Primary property evidence",
            "care_services_inferred": False,
        }],
    }


def test_primary_evidence_requires_exact_candidate_identity():
    result = verify([candidate()], evidence(address="999 OTHER ST"), probe_primary=False)
    assert result["counts"]["identity_failures"] == 1
    assert result["records"][0]["classification"] == "UNKNOWN"


def test_confirmed_primary_becomes_canonical_independent_living():
    verification = verify([candidate()], evidence(), probe_primary=False)
    payload = build([], [], [candidate()], verification)
    assert payload["report"]["independent_living_confirmed"] == 1
    assert payload["report"]["independent_living_candidates_unknown_active_unique"] == 0
    assert payload["records"][0]["canonical_type"] == "INDEPENDENT_LIVING"
    assert payload["records"][0]["business_license_id"] == "A01-1"
    assert payload["records"][0]["independent_living_classification"] == "CONFIRMED"


def test_primary_false_positive_is_not_added_to_universe():
    verification = verify([candidate()], evidence(classification="NOT_INDEPENDENT_LIVING_PRIMARY"), probe_primary=False)
    payload = build([], [], [candidate()], verification)
    assert payload["report"]["independent_living_false_positive_primary"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 0
    assert payload["report"]["independent_living_candidates_unknown_active_unique"] == 0


def test_unknown_primary_state_remains_review_candidate():
    verification = verify([candidate()], evidence(classification="UNKNOWN"), probe_primary=False)
    payload = build([], [], [candidate()], verification)
    assert payload["report"]["independent_living_confirmed"] == 0
    assert payload["report"]["canonical_facilities_unique"] == 0
    assert payload["report"]["independent_living_candidates_unknown_active_unique"] == 1


def test_same_exact_existing_identity_is_enriched_not_duplicated():
    alis = [{
        "facility_name": "SUNSET SENIOR APARTMENTS",
        "license_type": "AGC",
        "license_number": "100-AGC-1",
        "status": "Active",
        "expiration_date": "12/31/2026",
        "disciplinary_action": "N",
        "address": "1 SUNSET ST",
        "city": "LAS VEGAS",
        "state": "NV",
        "zip": "89101",
        "phone": "UNKNOWN",
        "first_issue_date": "01/01/2020",
        "primary_contact_name": "UNKNOWN",
        "primary_contact_role": "UNKNOWN",
        "capacity": "9",
        "federal_provider_number": "UNKNOWN",
        "detail_url": "https://example.invalid/detail",
        "official_detail": "{}",
        "memory_care_evidence": "[]",
        "memory_care_classification": "UNKNOWN",
        "county": "Clark",
        "is_clark_county": "true",
        "is_las_vegas_valley": "true",
    }]
    verification = verify([candidate()], evidence(), probe_primary=False)
    payload = build(alis, [], [candidate()], verification)
    assert payload["report"]["canonical_facilities_unique"] == 1
    assert payload["report"]["independent_living_confirmed"] == 1
    assert payload["report"]["independent_living_enriched_existing_identity"] == 1
    assert "INDEPENDENT_LIVING" in payload["records"][0]["facility_modalities"]


def test_distinct_business_licenses_same_campus_remain_distinct_entities():
    c1 = candidate("A01-1", "MCKNIGHT SENIOR I", "651 MCKNIGHT ST")
    c2 = candidate("A01-2", "MCKNIGHT SENIOR II", "651 MCKNIGHT ST")
    e = {
        "policy": {},
        "records": [
            {**evidence("A01-1", "MCKNIGHT SENIOR I", "651 MCKNIGHT ST")["records"][0]},
            {**evidence("A01-2", "MCKNIGHT SENIOR II", "651 MCKNIGHT ST")["records"][0]},
        ],
    }
    verification = verify([c1, c2], e, probe_primary=False)
    payload = build([], [], [c1, c2], verification)
    assert payload["report"]["canonical_facilities_unique"] == 2
    assert payload["report"]["independent_living_confirmed"] == 2
    assert payload["report"]["multi_entity_campuses"] == 1
