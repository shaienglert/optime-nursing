from __future__ import annotations

import json
from pathlib import Path

from app.services.personal_care_agency_runtime import (
    build_care_agency_requirements,
    evaluate_personal_care_agency,
    load_personal_care_agency_evidence,
    rank_compatible_agencies,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "pca_live_operational_allowlist.json"


def requirements():
    return build_care_agency_requirements(
        temporary_adl_support=True,
        bathing=True,
        dressing=True,
        transfer=True,
        preferred_languages=["Hebrew"],
    )


def test_license_only_does_not_invent_operational_fit():
    agency = {
        "license_number": "PCA-1",
        "agency_name": "Licensed Agency",
        "license_status": "Active",
        "serves_las_vegas_valley": True,
    }
    fit = evaluate_personal_care_agency(agency, requirements())
    assert fit["hard_gate"] == "UNKNOWN"
    assert "ACTIVE_HCQC_LICENSE" in fit["matched"]
    assert "BATHING_ASSISTANCE" in fit["material_unknowns"]
    assert "MINIMUM_BILLABLE_HOURS" in fit["material_unknowns"]


def test_missing_required_adl_service_is_hard_fail():
    agency = {
        "license_status": "Active",
        "serves_las_vegas_valley": True,
        "bathing_assistance": True,
        "dressing_assistance": True,
        "transfer_assistance": False,
    }
    fit = evaluate_personal_care_agency(agency, requirements())
    assert fit["hard_gate"] == "FAIL"
    assert "MISSING_TRANSFER_ASSISTANCE" in fit["hard_fail_reasons"]


def test_verified_short_visit_agency_can_pass():
    agency = {
        "license_number": "PCA-2",
        "agency_name": "Short Visit Agency",
        "license_status": "Active",
        "serves_las_vegas_valley": True,
        "bathing_assistance": True,
        "dressing_assistance": True,
        "transfer_assistance": True,
        "minimum_visit_minutes": 60,
        "minimum_billable_hours": 1,
        "employment_model": "W-2",
        "liability_insurance_verified": True,
        "workers_comp_verified": True,
        "background_check_verified": True,
        "fixed_caregiver_possible": True,
        "supervision_frequency": "Monthly and as needed",
        "languages": ["English", "Hebrew"],
        "availability_status": "AVAILABLE",
        "hourly_rate": 35,
    }
    fit = evaluate_personal_care_agency(agency, requirements())
    assert fit["hard_gate"] == "PASS"
    assert fit["evidence_completeness"] == 1.0


def test_failed_license_never_ranks():
    good = {
        "agency_name": "Good",
        "license_status": "Active",
        "serves_las_vegas_valley": True,
    }
    bad = {
        "agency_name": "Bad",
        "license_status": "Expired",
        "serves_las_vegas_valley": True,
    }
    ranked = rank_compatible_agencies([bad, good], requirements())
    assert [row["agency_name"] for row in ranked] == ["Good"]


def test_runtime_only_loads_primary_evidence_that_is_on_live_hcqc_allowlist():
    load_personal_care_agency_evidence.cache_clear()
    payload = load_personal_care_agency_evidence()
    licenses = {row["license_number"] for row in payload["records"]}
    allowlist = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    expected = {str(v).strip() for v in allowlist.get("license_numbers") or [] if str(v).strip()}
    assert len(expected) == 14
    assert payload["operationally_verified_count"] == len(expected)
    assert payload["live_operational_allowlist_count"] == len(expected)
    assert licenses == expected
    assert {"7602-PCS-15", "10330-PCS-5", "7836-PCS-13"} <= licenses
    assert not ({"8716-PCS-0", "8472-PCS-0", "11554-PCS-0", "9599-PCS-3"} & licenses)
