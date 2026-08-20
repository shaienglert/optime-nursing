from __future__ import annotations

"""Governed Personal Care Agency matching layer for Nevada Independent Living.

This module does not rank on marketing claims. Regulatory identity/status comes
from Nevada HCQC/ALiS; operational facts are separate evidence fields and remain
UNKNOWN until verified.
"""

from typing import Any, Dict, Iterable, List

UNKNOWN = "UNKNOWN"

REQUIRED_PCA_FIELDS = (
    "license_status",
    "serves_las_vegas_valley",
    "bathing_assistance",
    "dressing_assistance",
    "transfer_assistance",
    "minimum_visit_minutes",
    "minimum_billable_hours",
    "employment_model",
    "liability_insurance_verified",
    "workers_comp_verified",
    "background_check_verified",
    "fixed_caregiver_possible",
    "supervision_frequency",
    "languages",
    "availability_status",
    "hourly_rate",
)


def _known(value: Any) -> bool:
    return value not in (None, "", UNKNOWN, [], {})


def build_care_agency_requirements(*, temporary_adl_support: bool, bathing: bool, dressing: bool, transfer: bool, preferred_languages: Iterable[str] | None = None) -> Dict[str, Any]:
    return {
        "care_layer": "LICENSED_PERSONAL_CARE_AGENCY" if temporary_adl_support else UNKNOWN,
        "required_services": [
            key for key, needed in (
                ("BATHING_ASSISTANCE", bathing),
                ("DRESSING_ASSISTANCE", dressing),
                ("TRANSFER_ASSISTANCE", transfer),
            ) if needed
        ],
        "preferred_languages": [str(v) for v in (preferred_languages or []) if str(v).strip()],
        "preferred_operating_model": "ON_SITE_OR_LOW_MINIMUM_VISIT" if temporary_adl_support else UNKNOWN,
        "license_authority": "Nevada HCQC / ALiS",
        "license_type": "AGENCY_TO_PROVIDE_PERSONAL_CARE_SERVICES_IN_THE_HOME",
        "unknown_rule": "Operational facts remain UNKNOWN until directly verified with agency/provider evidence.",
    }


def evaluate_personal_care_agency(agency: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    hard_fail: List[str] = []
    unknown: List[str] = []
    match: List[str] = []

    status = str(agency.get("license_status") or UNKNOWN).upper()
    if status not in {"ACTIVE", UNKNOWN}:
        hard_fail.append("LICENSE_NOT_ACTIVE")
    elif status == UNKNOWN:
        unknown.append("LICENSE_STATUS")
    else:
        match.append("ACTIVE_HCQC_LICENSE")

    valley = agency.get("serves_las_vegas_valley", UNKNOWN)
    if valley is False:
        hard_fail.append("DOES_NOT_SERVE_LAS_VEGAS_VALLEY")
    elif valley == UNKNOWN:
        unknown.append("SERVICE_AREA")
    else:
        match.append("LAS_VEGAS_VALLEY_SERVICE")

    service_map = {
        "BATHING_ASSISTANCE": "bathing_assistance",
        "DRESSING_ASSISTANCE": "dressing_assistance",
        "TRANSFER_ASSISTANCE": "transfer_assistance",
    }
    for required in requirements.get("required_services") or []:
        field = service_map[required]
        value = agency.get(field, UNKNOWN)
        if value is False:
            hard_fail.append(f"MISSING_{required}")
        elif value == UNKNOWN:
            unknown.append(required)
        else:
            match.append(required)

    # These are decision-relevant but not legal-license facts. Missing evidence
    # never becomes a negative assertion.
    for field in ("minimum_billable_hours", "employment_model", "liability_insurance_verified", "workers_comp_verified", "background_check_verified", "fixed_caregiver_possible", "availability_status"):
        if not _known(agency.get(field)):
            unknown.append(field.upper())

    return {
        "agency_id": agency.get("agency_id") or agency.get("license_number") or UNKNOWN,
        "hard_gate": "FAIL" if hard_fail else ("UNKNOWN" if unknown else "PASS"),
        "hard_fail_reasons": sorted(set(hard_fail)),
        "matched": sorted(set(match)),
        "material_unknowns": sorted(set(unknown)),
        "evidence_completeness": sum(1 for field in REQUIRED_PCA_FIELDS if _known(agency.get(field))) / len(REQUIRED_PCA_FIELDS),
        "policy": "License/service incompatibility may exclude an agency; missing commercial or operational evidence remains UNKNOWN and never becomes a negative fact.",
    }


def rank_compatible_agencies(agencies: Iterable[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    evaluated = []
    for agency in agencies:
        result = evaluate_personal_care_agency(agency, requirements)
        if result["hard_gate"] == "FAIL":
            continue
        evaluated.append({**agency, "care_agency_fit": result})
    evaluated.sort(key=lambda row: (
        0 if row["care_agency_fit"]["hard_gate"] == "PASS" else 1,
        -float(row["care_agency_fit"]["evidence_completeness"]),
        str(row.get("agency_name") or ""),
    ))
    return evaluated


__all__ = ["build_care_agency_requirements", "evaluate_personal_care_agency", "rank_compatible_agencies"]
