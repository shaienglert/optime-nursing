from __future__ import annotations

"""Governed Personal Care Agency matching layer for Nevada Independent Living.

This module does not rank on marketing claims. Regulatory identity/status comes
from Nevada HCQC/ALiS; operational facts are separate evidence fields and remain
UNKNOWN until verified.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

UNKNOWN = "UNKNOWN"
REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATIONAL_EVIDENCE_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "personal_care_agency_operational_evidence.json"
LIVE_PROMOTIONS_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "pca_operational_live_promotions.json"
LIVE_OPERATIONAL_ALLOWLIST_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "pca_live_operational_allowlist.json"

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


def _load_live_operational_allowlist() -> set[str]:
    if not LIVE_OPERATIONAL_ALLOWLIST_PATH.is_file():
        return set()
    payload = json.loads(LIVE_OPERATIONAL_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return {
        str(value).strip()
        for value in payload.get("license_numbers") or []
        if str(value).strip()
    }


def _load_identity_verified_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        row
        for row in payload.get("records") or []
        if row.get("identity_verified") is True
        and str(row.get("license_number") or "").strip()
    ]


@lru_cache(maxsize=1)
def load_personal_care_agency_evidence() -> Dict[str, Any]:
    if not OPERATIONAL_EVIDENCE_PATH.is_file():
        return {
            "schema_version": "UNKNOWN",
            "source_snapshot": {},
            "records": [],
            "policy": {"unknown_rule": "No operational evidence file is available."},
        }
    payload = json.loads(OPERATIONAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
    live_allowlist = _load_live_operational_allowlist()
    combined = [
        *_load_identity_verified_records(OPERATIONAL_EVIDENCE_PATH),
        *_load_identity_verified_records(LIVE_PROMOTIONS_PATH),
    ]
    by_license: dict[str, dict[str, Any]] = {}
    for row in combined:
        license_number = str(row.get("license_number") or "").strip()
        by_license[license_number] = row
    records = [
        row
        for license_number, row in by_license.items()
        if license_number in live_allowlist
    ]
    records.sort(key=lambda row: (str(row.get("city") or ""), str(row.get("agency_name") or ""), str(row.get("license_number") or "")))
    payload = dict(payload)
    payload["records"] = records
    payload["operationally_verified_count"] = len(records)
    payload["live_operational_allowlist_count"] = len(live_allowlist)
    payload["governance"] = {
        "operational_evidence_required": True,
        "live_hcqc_allowlist_required": True,
        "rule": "A PCA is surfaced only when primary-provider identity evidence and the current HCQC/ALiS live-license allowlist agree.",
    }
    return payload


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

    for field in ("minimum_billable_hours", "employment_model", "liability_insurance_verified", "workers_comp_verified", "background_check_verified", "fixed_caregiver_possible", "availability_status"):
        if not _known(agency.get(field)):
            unknown.append(field.upper())

    preferred_languages = [str(v).strip().lower() for v in requirements.get("preferred_languages") or [] if str(v).strip()]
    if preferred_languages:
        available_languages = [str(v).strip().lower() for v in agency.get("languages") or [] if str(v).strip()]
        if not available_languages:
            unknown.append("PREFERRED_LANGUAGE")
        elif any(language in available_languages for language in preferred_languages):
            match.append("PREFERRED_LANGUAGE")
        else:
            hard_fail.append("PREFERRED_LANGUAGE_NOT_AVAILABLE")

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


def build_verified_care_partner_context(requirements: Dict[str, Any], *, limit: int = 10) -> Dict[str, Any]:
    payload = load_personal_care_agency_evidence()
    ranked = rank_compatible_agencies(payload.get("records") or [], requirements)
    snapshot = payload.get("source_snapshot") if isinstance(payload.get("source_snapshot"), dict) else {}
    options = []
    for row in ranked[: max(0, int(limit))]:
        options.append({
            "agency_id": row.get("agency_id") or UNKNOWN,
            "agency_name": row.get("agency_name") or UNKNOWN,
            "license_number": row.get("license_number") or UNKNOWN,
            "license_status": row.get("license_status") or UNKNOWN,
            "address": row.get("address") or UNKNOWN,
            "city": row.get("city") or UNKNOWN,
            "zip": row.get("zip") or UNKNOWN,
            "phone": row.get("phone") or UNKNOWN,
            "primary_source_url": row.get("primary_source_url") or UNKNOWN,
            "bathing_assistance": row.get("bathing_assistance", UNKNOWN),
            "dressing_assistance": row.get("dressing_assistance", UNKNOWN),
            "transfer_assistance": row.get("transfer_assistance", UNKNOWN),
            "minimum_visit_minutes": row.get("minimum_visit_minutes", UNKNOWN),
            "minimum_billable_hours": row.get("minimum_billable_hours", UNKNOWN),
            "hourly_rate": row.get("hourly_rate", UNKNOWN),
            "fixed_caregiver_possible": row.get("fixed_caregiver_possible", UNKNOWN),
            "languages": row.get("languages") or [],
            "availability_status": row.get("availability_status", UNKNOWN),
            "care_agency_fit": row.get("care_agency_fit") or {},
        })
    return {
        "status": "CANDIDATES_PENDING_OPERATIONAL_VERIFICATION" if options else "RESEARCH_REQUIRED",
        "requirements": requirements,
        "licensed_valley_universe_count": snapshot.get("las_vegas_valley_records", UNKNOWN),
        "operationally_verified_count": payload.get("operationally_verified_count", 0),
        "candidate_options": options,
        "decision_rule": "A licensed agency is not treated as fully suitable until visit minimums, short-visit economics, availability and any facility-specific access restrictions are verified.",
        "unknown_rule": "Missing operational evidence remains UNKNOWN and keeps the care-partner recommendation provisional.",
    }


__all__ = [
    "build_care_agency_requirements",
    "build_verified_care_partner_context",
    "evaluate_personal_care_agency",
    "load_personal_care_agency_evidence",
    "rank_compatible_agencies",
]
