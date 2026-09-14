from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = (
    REPO_ROOT
    / "docs"
    / "agent_specs"
    / "skills"
    / "supplier-intelligence"
    / "scripts"
    / "validate_supplier_record.py"
)


def _validator_module():
    spec = importlib.util.spec_from_file_location("supplier_record_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_record() -> dict:
    return {
        "supplier_id": "las-vegas-example-home-care",
        "legal_name": "Example Home Care LLC",
        "brand_name": "Example Home Care",
        "sector_ids": ["HOME_CARE"],
        "branch": {
            "address": "Las Vegas, NV",
            "phone": "+1-702-555-0100",
            "website": "https://example.invalid",
            "service_area": ["Las Vegas"],
            "las_vegas_valley_verified": True,
        },
        "services": [],
        "payment_options": [],
        "licenses": [],
        "ratings": [
            {
                "source": "Google Maps",
                "branch_identity": "Las Vegas branch",
                "rating": 4.8,
                "review_count": 120,
                "observed_at": "2026-09-14T00:00:00Z",
                "source_url": "https://example.invalid/reviews",
            }
        ],
        "facility_referrals": [],
        "oomnik_feedback": {"status": "NOT_YET_AVAILABLE", "verified_review_count": 0, "dimensions": {}},
        "involvement": "OUTCOME_CRITICAL",
        "critical_readiness": {"capacity_confirmed": False, "unresolved_blockers": ["NOT_CONTACTED"]},
        "commercial_relationship": {"status": "NONE_KNOWN", "disclosure": None},
        "evidence_refs": ["evidence-1"],
        "unknown_fields": [],
        "conflicts": [],
        "freshness": {"last_verified_at": "2026-09-14T00:00:00Z", "status": "FRESH"},
        "publication": {"status": "VERIFIED", "reasons": []},
    }


def test_supplier_record_validator_accepts_governed_record() -> None:
    validator = _validator_module()
    assert validator.validate(_valid_record()) == []


def test_supplier_record_validator_rejects_unverified_geography_and_missing_readiness() -> None:
    validator = _validator_module()
    record = _valid_record()
    record["branch"]["las_vegas_valley_verified"] = False
    record["critical_readiness"] = None
    errors = validator.validate(record)
    assert "Las Vegas Valley service must be verified" in errors
    assert "OUTCOME_CRITICAL supplier requires critical_readiness" in errors


def test_supplier_record_validator_rejects_synthetic_rating_without_provenance() -> None:
    validator = _validator_module()
    record = _valid_record()
    del record["ratings"][0]["source_url"]
    assert "ratings[0] missing source_url" in validator.validate(record)

