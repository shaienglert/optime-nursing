"""Where the evidence for each SYSTEM/CLIENT MUST comes from -- one declared registry.

Owner rule (2026-10-01): before a market (or the pilot) counts as ready, every MUST the
engine can ask for must have at least one defined evidence source in that market. With no
source, a zero result is a catalog readiness problem, not "no suitable communities".

The evaluators in client_intent_runtime read exactly these sources, and the decision core
loads every parameter listed here, so a MUST can never depend on evidence that is never
fetched (the secured_units gap: the evaluator read it, the core never loaded it).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

MUST_EVIDENCE_SOURCES: Dict[str, Dict[str, List[str]]] = {
    "LICENSE_CURRENTLY_VALID": {"canonical_fields": ["license_status", "expiration_date"]},
    "LAS_VEGAS": {"canonical_fields": ["city", "state"]},
    "LAS_VEGAS_CITY_LIMITS": {"canonical_fields": ["city", "state"]},
    "ADL_SUPPORT_AVAILABLE": {"parameters": ["adl_support"], "payload_fields": ["adl_support_verified", "outside_care_allowed_verified"]},
    "MEDICATION_SUPPORT_AVAILABLE": {"parameters": ["medication_support"], "payload_fields": ["medication_support_verified"]},
    "NO_FORCED_MEMORY_PLACEMENT": {"canonical_fields": ["canonical_type", "synthetic_archetype"]},
    "RECOVERY_TRANSITION_COMPATIBLE": {"canonical_fields": ["housing_modalities"], "payload_fields": ["outside_care_allowed_verified", "continuum_of_care_verified", "same_apartment_transition_verified"]},
    "REHAB_PATH_AVAILABLE": {"parameters": ["pt", "ot"], "payload_fields": ["rehab_verified", "pt_ot_verified", "pt_ot_external_path_verified"]},
    "POST_HOSPITAL_REHAB_PROGRAM": {"parameters": ["pt", "ot", "therapy_staffing", "nursing_24_7"], "payload_fields": ["post_hospital_rehab_program_verified", "nursing_support_verified", "physician_coordination_verified"], "provider_capabilities": ["continuum_rehabilitation"]},
    "SECURED_UNIT_AVAILABLE": {"parameters": ["secured_units"]},
    "SECURE_MEMORY_CARE_CONFIRMED": {"canonical_fields": ["memory_care_classification"]},
    "COUPLE_CORESIDENCE": {"canonical_fields": ["accepts_couples"], "payload_fields": ["couple_coresidence_verified", "same_apartment_transition_verified"]},
    "KOSHER_MEALS": {"parameters": ["kosher"]},
    "REQUIRED_LANGUAGE_SUPPORT": {"parameters": ["languages"]},
    "REQUIRED_ACTIVITIES": {"parameters": ["activities"]},
    "CONTINUUM_OF_CARE_REQUIRED": {"canonical_fields": ["housing_modalities", "synthetic_archetype"], "payload_fields": ["continuum_of_care_verified"]},
    "CURRENT_AVAILABILITY_FOR_URGENT_MOVE": {"parameters": ["current_availability"]},
    "MEDICAID_PATHWAY_REQUIRED": {"parameters": ["medicaid_attributes"], "payload_fields": ["medicaid_accepted_verified"]},
}

MUST_EVIDENCE_PARAMETER_IDS = frozenset(
    parameter for spec in MUST_EVIDENCE_SOURCES.values() for parameter in spec.get("parameters", [])
)


def _known(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return str(value).strip().upper() not in {"", "UNKNOWN", "NONE"}


def market_must_coverage(keys: Iterable[str] | None = None) -> Dict[str, Any]:
    """Count, per MUST, the facilities in the configured market with a known value from a
    declared source. A MUST with zero is a readiness gap for that market."""
    from app.services.facility_parameter_service import get_canonical_facility_index, get_facility_parameter_table

    index = get_canonical_facility_index()
    keys = list(keys or MUST_EVIDENCE_SOURCES)
    parameters = sorted(MUST_EVIDENCE_PARAMETER_IDS)
    values: Dict[str, Dict[str, Any]] = {}
    for cid in index:
        table = get_facility_parameter_table(cid, priority_parameter_ids=parameters, include_evidence_records=False)
        values[cid] = {
            row["parameter_id"]: row.get("raw_value")
            for row in table.get("rows") or []
            if row.get("parameter_id") in MUST_EVIDENCE_PARAMETER_IDS
        }
    report: Dict[str, Any] = {}
    for key in keys:
        spec = MUST_EVIDENCE_SOURCES.get(key)
        if spec is None:
            report[key] = {"status": "NO_DECLARED_SOURCE", "facilities_with_evidence": 0}
            continue
        covered = 0
        for cid, record in index.items():
            payload = record.get("pilot_service_evidence") if isinstance(record.get("pilot_service_evidence"), dict) else {}
            if (
                any(_known(values[cid].get(p)) for p in spec.get("parameters", []))
                or any(_known(record.get(f)) for f in spec.get("canonical_fields", []))
                or any(isinstance(payload.get(f), bool) for f in spec.get("payload_fields", []))
            ):
                covered += 1
        report[key] = {"status": "COVERED" if covered else "NO_EVIDENCE_IN_MARKET", "facilities_with_evidence": covered, "facilities": len(index)}
    return report


__all__ = ["MUST_EVIDENCE_SOURCES", "MUST_EVIDENCE_PARAMETER_IDS", "market_must_coverage"]
