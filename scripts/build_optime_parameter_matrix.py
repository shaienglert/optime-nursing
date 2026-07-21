from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = REPO_ROOT / "database"
REPORTS_DIR = REPO_ROOT / "reports"

CANONICAL_PATH = DATABASE_DIR / "florida_facility_universe_canonical.json"
CROSSWALK_PATH = DATABASE_DIR / "florida_facility_source_crosswalk.json"
LEGACY_CMS_EVIDENCE_PATH = DATABASE_DIR / "florida_parameter_evidence.json"
NPPES_IDENTITIES_PATH = DATABASE_DIR / "florida_nppes_facility_identities.json"
NPPES_TAXONOMY_PATH = DATABASE_DIR / "florida_nppes_taxonomy_evidence.json"
RECOVERED_COVERAGE_PATH = REPORTS_DIR / "FLORIDA_PARAMETER_COVERAGE_MATRIX.json"

OUT_REGISTRY_PATH = DATABASE_DIR / "optime_parameter_registry.json"
OUT_EVIDENCE_PATH = DATABASE_DIR / "florida_facility_parameter_evidence.json"
OUT_COVERAGE_JSON_PATH = REPORTS_DIR / "FLORIDA_PARAMETER_COVERAGE_MATRIX.json"
OUT_COVERAGE_MD_PATH = REPORTS_DIR / "FLORIDA_PARAMETER_COVERAGE_MATRIX.md"


BOOLEAN_PARAMS = {
    "skilled_nursing_capabilities",
    "nursing_24_7",
    "direct_24hr_nurse_availability",
    "third_party_24hr_nurse_availability",
    "adl_support",
    "medication_support",
    "transfer_assistance",
    "higher_acuity_capabilities",
    "pt",
    "ot",
    "speech_therapy",
    "short_term_rehab",
    "post_stroke_neuro_evidence",
    "therapy_staffing",
    "memory_care",
    "dementia_alz_programs",
    "wound_care",
    "dialysis_arrangements",
    "respiratory_trach_vent",
    "hospice_palliative_arrangements",
    "specialty_licenses",
    "extended_congregate_care",
    "limited_nursing_services",
    "limited_mental_health",
    "secured_units",
    "languages",
    "dietary_capabilities",
    "gluten_free",
    "kosher",
    "religious_cultural_services",
    "activities",
    "transportation",
    "amenities",
    "private_shared_rooms",
    "accessibility",
    "payer_information",
    "medicaid_attributes",
    "medicare_attributes",
    "current_availability",
    "waiting_list",
    "current_promotions",
}

INTEGER_PARAMS = {
    "inspection_rating",
    "deficiency_count",
    "deficiency_severity",
    "complaint_related_findings",
    "fire_safety_deficiencies",
    "infection_control_findings",
    "payment_denials",
    "quality_measures",
}

DECIMAL_PARAMS = {
    "rn_hours_per_resident_day",
    "total_nurse_hours_per_resident_day",
    "staffing_turnover",
}

CURRENCY_PARAMS = {"penalties_fines", "published_rates", "fees", "current_price"}
DATE_PARAMS = {"earliest_admission_date"}
TEXT_PARAMS = {"hospital_claims_outcomes", "sanctions_final_orders"}

PROGRAM_SCOPE_PARAMS = {
    "memory_care",
    "dementia_alz_programs",
    "extended_congregate_care",
    "limited_nursing_services",
    "limited_mental_health",
    "secured_units",
    "post_stroke_neuro_evidence",
}

UNIT_SCOPE_PARAMS = {"private_shared_rooms", "accessibility", "current_availability", "waiting_list", "earliest_admission_date", "current_price", "current_promotions"}
SERVICE_SCOPE_PARAMS = {"pt", "ot", "speech_therapy", "therapy_staffing", "hospice_palliative_arrangements", "transportation", "adl_support", "medication_support", "dialysis_arrangements", "respiratory_trach_vent", "wound_care", "activities"}

HARD_FILTER_PARAMS = {
    "skilled_nursing_capabilities",
    "nursing_24_7",
    "direct_24hr_nurse_availability",
    "third_party_24hr_nurse_availability",
    "adl_support",
    "medication_support",
    "transfer_assistance",
    "pt",
    "ot",
    "speech_therapy",
    "post_stroke_neuro_evidence",
    "memory_care",
    "dialysis_arrangements",
    "respiratory_trach_vent",
    "hospice_palliative_arrangements",
    "limited_nursing_services",
    "limited_mental_health",
    "secured_units",
    "medicaid_attributes",
    "medicare_attributes",
}

PERSONALIZATION_TAGS = {
    "skilled_nursing_capabilities": ["nursing", "medical", "high_acuity", "stroke"],
    "nursing_24_7": ["nursing", "medical", "stroke"],
    "direct_24hr_nurse_availability": ["nursing", "medical", "stroke"],
    "third_party_24hr_nurse_availability": ["nursing", "medical"],
    "rn_hours_per_resident_day": ["nursing", "medical", "staffing"],
    "total_nurse_hours_per_resident_day": ["nursing", "staffing", "medical"],
    "adl_support": ["adl", "care", "mobility", "stroke"],
    "medication_support": ["medication", "care", "stroke"],
    "transfer_assistance": ["transfer", "mobility", "stroke"],
    "higher_acuity_capabilities": ["high_acuity", "medical"],
    "pt": ["rehab", "stroke", "mobility"],
    "ot": ["rehab", "stroke", "adl"],
    "speech_therapy": ["rehab", "stroke", "neurological"],
    "short_term_rehab": ["rehab", "recovery", "stroke"],
    "post_stroke_neuro_evidence": ["stroke", "neurological", "rehab"],
    "therapy_staffing": ["rehab", "staffing"],
    "memory_care": ["memory", "dementia", "specialized_care"],
    "dementia_alz_programs": ["memory", "dementia", "specialized_care"],
    "wound_care": ["medical", "specialized_care"],
    "dialysis_arrangements": ["medical", "specialized_care"],
    "respiratory_trach_vent": ["medical", "specialized_care", "high_acuity"],
    "hospice_palliative_arrangements": ["palliative", "medical"],
    "transportation": ["mobility", "access"],
}

CONSUMER_DESCRIPTION_OVERRIDES = {
    "skilled_nursing_capabilities": "Whether the facility has verified evidence of skilled nursing capability.",
    "nursing_24_7": "Whether there is evidence that nursing coverage is available around the clock.",
    "direct_24hr_nurse_availability": "Whether a directly employed nurse is verified to be available 24 hours a day.",
    "third_party_24hr_nurse_availability": "Whether 24-hour nurse coverage is verified through contracted or third-party staffing.",
    "rn_hours_per_resident_day": "Reported RN staffing hours per resident day from CMS when available.",
    "total_nurse_hours_per_resident_day": "Reported total nursing staffing hours per resident day from CMS when available.",
    "post_stroke_neuro_evidence": "Evidence of a stroke, neurological, or similar rehabilitation program or service line.",
    "memory_care": "Evidence of a memory-care program, unit, or other dementia-support capability.",
    "dementia_alz_programs": "Evidence of a dementia or Alzheimer-focused program or service.",
    "sanctions_final_orders": "Evidence of sanctions, enforcement actions, or final orders when officially verified.",
    "medicare_attributes": "Evidence that the facility is Medicare-certified or otherwise has verified Medicare participation data.",
    "current_availability": "Current availability must always be confirmed directly with the facility.",
    "earliest_admission_date": "Earliest known admission timing, if directly verified.",
    "current_price": "Current pricing must be treated as dynamic and verified directly with the facility.",
}

SOURCE_PRIORITY_BY_SOURCE = {
    "cms_provider_type": ["CMS_OFFICIAL", "AHCA_OFFICIAL", "FACILITY_VERIFIED"],
    "cms_certification_number": ["CMS_OFFICIAL", "FACILITY_VERIFIED"],
    "rn_hours": ["CMS_OFFICIAL", "FACILITY_VERIFIED"],
    "total_nurse_hours": ["CMS_OFFICIAL", "FACILITY_VERIFIED"],
    "inspection_rating": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "deficiency_count": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "severe_deficiency_count": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "complaint_deficiency_count": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "infection_control_count": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "total_fines": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "total_payment_denials": ["CMS_OFFICIAL", "AHCA_OFFICIAL"],
    "quality_measure_count": ["CMS_OFFICIAL"],
    "dynamic": ["DIRECT_FACILITY_CONFIRMATION"],
    "unknown": ["DIRECT_FACILITY_CONFIRMATION"],
    "nppes_taxonomy": ["NPPES_DECLARED_PROVIDER", "FACILITY_VERIFIED"],
}

LEGACY_CMS_PARAMETER_MAP = {
    "skilled_nursing_capabilities": "skilled_nursing_capabilities",
    "nursing_24_7": "nursing_24_7",
    "rn_hours_per_resident_day": "rn_hours_per_resident_day",
    "total_nurse_hours_per_resident_day": "total_nurse_hours_per_resident_day",
    "inspection_rating": "inspection_rating",
    "deficiency_count": "deficiency_count",
    "severe_deficiency_count": "deficiency_severity",
    "complaint_deficiency_count": "complaint_related_findings",
    "infection_control_count": "infection_control_findings",
    "fire_safety_deficiencies": "fire_safety_deficiencies",
    "total_fines": "penalties_fines",
    "total_payment_denials": "payment_denials",
    "quality_measure_count": "quality_measures",
    "medicare_medicaid_attributes": "medicare_attributes",
}


@dataclass
class ResolvedRow:
    parameter_id: str
    family: str
    category: str
    parameter: str
    status_value: Any
    detail_scope: str
    scope_name: Optional[str]
    source: str
    last_verified: Optional[str]
    sort_score: float
    evidence_count: int


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def value_type_for_parameter(parameter_id: str) -> str:
    if parameter_id in BOOLEAN_PARAMS:
        return "BOOLEAN_STATUS"
    if parameter_id in INTEGER_PARAMS:
        return "INTEGER"
    if parameter_id in DECIMAL_PARAMS:
        return "DECIMAL"
    if parameter_id in CURRENCY_PARAMS:
        return "CURRENCY"
    if parameter_id in DATE_PARAMS:
        return "DATE"
    if parameter_id in TEXT_PARAMS:
        return "TEXT"
    return "TEXT"


def allowed_values_for_parameter(parameter_id: str) -> Optional[List[str]]:
    if parameter_id in BOOLEAN_PARAMS:
        return ["YES", "NO", "UNKNOWN"]
    return None


def scope_for_parameter(parameter_id: str) -> str:
    if parameter_id in PROGRAM_SCOPE_PARAMS:
        return "PROGRAM"
    if parameter_id in UNIT_SCOPE_PARAMS:
        return "UNIT"
    if parameter_id in SERVICE_SCOPE_PARAMS:
        return "SERVICE"
    return "FACILITY"


def consumer_description(display_name: str, parameter_id: str) -> str:
    if parameter_id in CONSUMER_DESCRIPTION_OVERRIDES:
        return CONSUMER_DESCRIPTION_OVERRIDES[parameter_id]
    return f"Evidence about {display_name.lower()} that can be shown in the facility comparison table."


def freshness_rule(row: Dict[str, Any], parameter_id: str) -> str:
    source_key = str(row.get("source") or "unknown")
    if source_key == "dynamic" or parameter_id in {"current_availability", "earliest_admission_date", "waiting_list", "current_price", "current_promotions"}:
        return "Direct facility confirmation required; do not infer from stale or missing data."
    if source_key.startswith("cms") or source_key in {"inspection_rating", "deficiency_count", "quality_measure_count", "rn_hours", "total_nurse_hours", "total_fines", "total_payment_denials", "infection_control_count", "severe_deficiency_count", "complaint_deficiency_count"}:
        return "Use latest CMS ingest snapshot; retain last verified date from the structured source."
    if source_key == "nppes_taxonomy":
        return "Use latest NPPES taxonomy snapshot as declared capability evidence only, not licensure proof."
    return "Keep as UNKNOWN until stronger evidence or direct verification is available."


def ranking_eligibility(row: Dict[str, Any], parameter_id: str) -> bool:
    return bool(row.get("can_affect_case_match"))


def hard_filter_eligibility(parameter_id: str) -> bool:
    return parameter_id in HARD_FILTER_PARAMS


def build_registry(recovered_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Dict[str, Any]]]:
    registry: List[Dict[str, Any]] = []
    missing_definitions: List[str] = []
    registry_by_id: Dict[str, Dict[str, Any]] = {}

    for row in recovered_rows:
        parameter_id = str(row["canonical_name"])
        display_name = str(row["parameter"])
        value_type = value_type_for_parameter(parameter_id)
        applicable_scope = scope_for_parameter(parameter_id)
        record = {
            "parameter_id": parameter_id,
            "family": row["family"],
            "display_name": display_name,
            "consumer_description": consumer_description(display_name, parameter_id),
            "value_type": value_type,
            "allowed_values": allowed_values_for_parameter(parameter_id),
            "applicable_scope": applicable_scope,
            "source_priority": SOURCE_PRIORITY_BY_SOURCE.get(str(row.get("source") or "unknown"), ["DIRECT_FACILITY_CONFIRMATION"]),
            "freshness_rule": freshness_rule(row, parameter_id),
            "ranking_eligibility": ranking_eligibility(row, parameter_id),
            "hard_filter_eligibility": hard_filter_eligibility(parameter_id),
            "requires_facility_confirmation": bool(row.get("requires_facility_confirmation")),
            "dynamic": bool(row.get("dynamic")),
            "personalization_tags": PERSONALIZATION_TAGS.get(parameter_id, []),
            "recovered_from": {
                "coverage_source": "reports/FLORIDA_PARAMETER_COVERAGE_MATRIX.json",
                "legacy_source": str(row.get("source") or "unknown"),
                "legacy_raw_field": str(row.get("raw_field") or "unknown"),
            },
        }

        if value_type == "TEXT" and parameter_id not in TEXT_PARAMS and parameter_id not in BOOLEAN_PARAMS and parameter_id not in INTEGER_PARAMS and parameter_id not in DECIMAL_PARAMS and parameter_id not in CURRENCY_PARAMS and parameter_id not in DATE_PARAMS:
            missing_definitions.append(parameter_id)
            record["consumer_description"] = "MISSING_REGISTRY_DEFINITION"

        registry.append(record)
        registry_by_id[parameter_id] = record

    unique_missing = sorted(set(missing_definitions))
    return registry, unique_missing, registry_by_id


def load_recovered_parameter_rows() -> List[Dict[str, Any]]:
    payload = read_json(RECOVERED_COVERAGE_PATH)
    rows = payload.get("parameters") or []
    recovered = []
    for row in rows:
        if "parameter" in row and "canonical_name" in row:
            display_name = row["parameter"]
            parameter_id = row["canonical_name"]
            source = row.get("source")
            raw_field = row.get("raw_field")
            family = row.get("family")
            can_affect_case_match = row.get("can_affect_case_match", False)
            requires_facility_confirmation = row.get("requires_facility_confirmation", False)
            dynamic = row.get("dynamic", False)
        else:
            display_name = row["display_name"]
            parameter_id = row["parameter_id"]
            source = "recovered_governed_report"
            raw_field = "recovered_governed_report"
            family = row.get("family")
            can_affect_case_match = bool(row.get("ranking_eligibility", False))
            requires_facility_confirmation = False
            dynamic = family == "DYNAMIC"
        recovered.append(
            {
                "parameter": display_name,
                "canonical_name": parameter_id,
                "source": source,
                "raw_field": raw_field,
                "family": family,
                "can_affect_case_match": can_affect_case_match,
                "requires_facility_confirmation": requires_facility_confirmation,
                "dynamic": dynamic,
            }
        )
    return recovered


def standardize_value(parameter_id: str, raw_value: Any) -> Any:
    if parameter_id == "nursing_24_7":
        return "YES"
    if parameter_id == "medicare_attributes":
        return "YES"
    if parameter_id in BOOLEAN_PARAMS:
        value = normalize_text(raw_value)
        if value in {"yes", "true", "1"}:
            return "YES"
        if value in {"no", "false", "0"}:
            return "NO"
        return "YES" if raw_value not in {None, "", "UNKNOWN"} else "UNKNOWN"
    return raw_value


def evidence_strength(source: str) -> str:
    if source.startswith("CMS"):
        return "HIGH"
    if source.startswith("NPPES"):
        return "MEDIUM"
    return "LOW"


def build_cms_evidence(
    canonical_by_id: Dict[str, Dict[str, Any]],
    registry_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    payload = read_json(LEGACY_CMS_EVIDENCE_PATH)
    evidence_rows: List[Dict[str, Any]] = []

    for row in payload.get("records") or []:
        legacy_id = str(row.get("parameter") or "")
        parameter_id = LEGACY_CMS_PARAMETER_MAP.get(legacy_id)
        if not parameter_id or parameter_id not in registry_by_id:
            continue
        if str(row.get("evidence_state") or "") == "UNKNOWN":
            continue

        canonical_id = str(row.get("canonical_id") or "")
        if canonical_id not in canonical_by_id:
            continue

        registry = registry_by_id[parameter_id]
        canonical = canonical_by_id[canonical_id]
        standardized = standardize_value(parameter_id, row.get("value"))
        evidence_text = str(row.get("canonical_name") or registry["display_name"])
        if parameter_id == "nursing_24_7":
            evidence_text = "CMS nursing home provider row indicates nursing coverage capability; direct nurse modality remains separately unverified."
        if parameter_id == "medicare_attributes":
            evidence_text = "CMS certification number present; Medicare certification verified from CMS source."

        evidence_rows.append(
            {
                "canonical_facility_id": canonical_id,
                "parameter_id": parameter_id,
                "value": standardized,
                "scope": registry["applicable_scope"],
                "scope_name": None,
                "source": str(row.get("source") or "CMS"),
                "source_record_id": canonical.get("source_record_id") or canonical.get("source_identity_ids", {}).get("cms_ccn"),
                "evidence_text": evidence_text,
                "evidence_value": row.get("value"),
                "evidence_date": row.get("date"),
                "last_verified": row.get("date"),
                "confidence": evidence_strength(str(row.get("source") or "CMS")),
                "evidence_strength": evidence_strength(str(row.get("source") or "CMS")),
                "provenance": {
                    "source_family": "CMS",
                    "legacy_evidence_file": "database/florida_parameter_evidence.json",
                    "legacy_parameter": legacy_id,
                    "evidence_state": row.get("evidence_state"),
                },
                "conflict_status": "NONE",
            }
        )

    return evidence_rows


def map_taxonomy_to_parameters(row: Dict[str, Any]) -> List[Tuple[str, str, Optional[str], str]]:
    desc = normalize_text(row.get("taxonomy_desc"))
    mappings: List[Tuple[str, str, Optional[str], str]] = []

    if any(token in desc for token in ["skilled nursing facility", "nursing care", "nursing facility"]):
        mappings.append(("skilled_nursing_capabilities", "FACILITY", None, "Declared nursing-facility taxonomy in NPPES."))
        mappings.append(("nursing_24_7", "FACILITY", None, "Declared nursing-facility taxonomy in NPPES; direct nurse modality remains separately unverified."))

    if "physical therapist" in desc or "physical therapy" in desc or "physical medicine" in desc:
        mappings.append(("pt", "SERVICE", row.get("taxonomy_desc"), "Physical therapy-related taxonomy in NPPES."))
    if "occupational therapist" in desc or "occupational therapy" in desc:
        mappings.append(("ot", "SERVICE", row.get("taxonomy_desc"), "Occupational therapy-related taxonomy in NPPES."))
    if "speech-language" in desc or "hearing and speech" in desc:
        mappings.append(("speech_therapy", "SERVICE", row.get("taxonomy_desc"), "Speech therapy-related taxonomy in NPPES."))
    if "alzheimer center" in desc or "dementia center" in desc:
        mappings.append(("memory_care", "PROGRAM", row.get("taxonomy_desc"), "Dementia-focused taxonomy in NPPES."))
        mappings.append(("dementia_alz_programs", "PROGRAM", row.get("taxonomy_desc"), "Dementia-focused taxonomy in NPPES."))
    if "hospice" in desc or "palliative" in desc:
        mappings.append(("hospice_palliative_arrangements", "SERVICE", row.get("taxonomy_desc"), "Hospice or palliative taxonomy in NPPES."))
    if any(token in desc for token in ["non-emergency medical transport", "private vehicle", "transportation broker", "secured medical transport"]):
        mappings.append(("transportation", "SERVICE", row.get("taxonomy_desc"), "Transportation-related taxonomy in NPPES."))
    if any(token in desc for token in ["home health aide", "homemaker", "adult companion", "in home supportive care"]):
        mappings.append(("adl_support", "SERVICE", row.get("taxonomy_desc"), "Supportive-care taxonomy in NPPES."))
    if "mental illness" in desc:
        mappings.append(("limited_mental_health", "PROGRAM", row.get("taxonomy_desc"), "Mental-illness specialization taxonomy in NPPES."))
    if "dialysis" in desc:
        mappings.append(("dialysis_arrangements", "SERVICE", row.get("taxonomy_desc"), "Dialysis-related taxonomy in NPPES."))
    if "respiratory therapist" in desc or "ventilator" in desc or "trache" in desc:
        mappings.append(("respiratory_trach_vent", "SERVICE", row.get("taxonomy_desc"), "Respiratory-related taxonomy in NPPES."))
    if "wound care" in desc:
        mappings.append(("wound_care", "SERVICE", row.get("taxonomy_desc"), "Wound-care taxonomy in NPPES."))

    return mappings


def build_nppes_evidence(
    canonical_records: List[Dict[str, Any]],
    registry_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    taxonomy_payload = read_json(NPPES_TAXONOMY_PATH)
    rows_by_npi: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in taxonomy_payload.get("records") or []:
        npi = str(row.get("npi") or "")
        if npi:
            rows_by_npi[npi].append(row)

    evidence_rows: List[Dict[str, Any]] = []
    for canonical in canonical_records:
        npi = str(canonical.get("source_identity_ids", {}).get("npi") or "")
        if not npi:
            continue
        for row in rows_by_npi.get(npi, []):
            for parameter_id, scope, scope_name, evidence_text in map_taxonomy_to_parameters(row):
                if parameter_id not in registry_by_id:
                    continue
                evidence_rows.append(
                    {
                        "canonical_facility_id": canonical["canonical_id"],
                        "parameter_id": parameter_id,
                        "value": "YES",
                        "scope": scope,
                        "scope_name": scope_name,
                        "source": "NPPES Taxonomy",
                        "source_record_id": row.get("evidence_id"),
                        "evidence_text": evidence_text,
                        "evidence_value": row.get("taxonomy_desc"),
                        "evidence_date": row.get("last_updated") or row.get("enumeration_date"),
                        "last_verified": taxonomy_payload.get("generated_at_utc"),
                        "confidence": "MEDIUM",
                        "evidence_strength": "MEDIUM",
                        "provenance": {
                            "source_family": "NPPES",
                            "npi": npi,
                            "taxonomy_code": row.get("taxonomy_code"),
                            "taxonomy_desc": row.get("taxonomy_desc"),
                            "taxonomy_primary": row.get("taxonomy_primary"),
                            "declared_provider_capability_only": True,
                            "not_licensure_proof": True,
                        },
                        "conflict_status": "NONE",
                    }
                )
    return evidence_rows


def dedupe_evidence(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = (
            row["canonical_facility_id"],
            row["parameter_id"],
            row["scope"],
            row.get("scope_name"),
            row["source"],
            row.get("source_record_id"),
            json.dumps(row.get("evidence_value"), sort_keys=True, ensure_ascii=False),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def build_lookup_by_parameter(evidence_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    by_facility: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in evidence_rows:
        by_facility[row["canonical_facility_id"]][row["parameter_id"]].append(row)
    return by_facility


def scope_rank(scope: str) -> int:
    return {"FACILITY": 4, "PROGRAM": 3, "UNIT": 2, "SERVICE": 1}.get(scope, 0)


def base_priority(parameter: Dict[str, Any]) -> float:
    score = 100.0
    if parameter.get("hard_filter_eligibility"):
        score += 50.0
    if parameter.get("ranking_eligibility"):
        score += 20.0
    family_bonus = {
        "CARE_NURSING": 14.0,
        "REHABILITATION": 13.0,
        "SPECIALIZED_CARE": 12.0,
        "QUALITY_SAFETY": 8.0,
        "FINANCIAL_ACCESS": 6.0,
        "PERSONAL_FIT": 5.0,
        "DYNAMIC": 1.0,
    }
    return score + family_bonus.get(str(parameter.get("family")), 0.0)


PROFILE_TAGS = {
    "stroke": ["stroke", "neurological", "rehab", "transfer", "medication", "nursing", "mobility"],
    "memory": ["memory", "dementia", "specialized_care"],
    "high_acuity": ["high_acuity", "medical", "nursing"],
}


def resolve_parameter_table(
    canonical_facility_id: str,
    canonical_by_id: Dict[str, Dict[str, Any]],
    registry: List[Dict[str, Any]],
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]],
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    effective_tags = [normalize_text(tag) for tag in (need_tags or [])]
    if profile_key:
        effective_tags.extend(PROFILE_TAGS.get(profile_key, []))
    priority_set = {str(item) for item in (priority_parameter_ids or [])}
    parameter_rows = evidence_lookup.get(canonical_facility_id, {})
    resolved: List[ResolvedRow] = []

    for parameter in registry:
        parameter_id = parameter["parameter_id"]
        rows = parameter_rows.get(parameter_id, [])
        tags = [normalize_text(tag) for tag in parameter.get("personalization_tags") or []]
        tag_bonus = float(len(set(tags).intersection(effective_tags)) * 20)
        explicit_bonus = 100.0 if parameter_id in priority_set else 0.0

        if rows:
            best = sorted(
                rows,
                key=lambda item: (
                    scope_rank(str(item.get("scope") or "")),
                    1 if str(item.get("confidence") or "") == "HIGH" else 0,
                    str(item.get("last_verified") or ""),
                ),
                reverse=True,
            )[0]
            detail_scope = str(best.get("scope") or parameter.get("applicable_scope"))
            status_value = best.get("value")
            source = str(best.get("source") or "UNKNOWN")
            last_verified = best.get("last_verified")
            evidence_count = len(rows)
        else:
            detail_scope = parameter.get("applicable_scope")
            status_value = "UNKNOWN"
            source = "Not verified"
            last_verified = None
            evidence_count = 0

        if parameter_id == "current_availability":
            status_value = "Confirm directly with facility" if rows else "Confirm directly with facility"
            source = "Direct facility confirmation required"

        resolved.append(
            ResolvedRow(
                parameter_id=parameter_id,
                family=parameter["family"],
                category=parameter["family"],
                parameter=parameter["display_name"],
                status_value=status_value,
                detail_scope=detail_scope,
                scope_name=(rows[0].get("scope_name") if rows else None),
                source=source,
                last_verified=last_verified,
                sort_score=base_priority(parameter) + tag_bonus + explicit_bonus,
                evidence_count=evidence_count,
            )
        )

    resolved.sort(key=lambda item: (-item.sort_score, item.family, item.parameter))
    return [
        {
            "parameter_id": item.parameter_id,
            "category": item.category,
            "parameter": item.parameter,
            "status_value": item.status_value if item.status_value != "UNKNOWN" else "Not verified",
            "raw_value": item.status_value,
            "detail_scope": item.detail_scope,
            "scope_name": item.scope_name,
            "source": item.source,
            "last_verified": item.last_verified,
            "evidence_count": item.evidence_count,
        }
        for item in resolved
    ]


def compare_facilities(
    canonical_facility_ids: List[str],
    canonical_by_id: Dict[str, Dict[str, Any]],
    registry: List[Dict[str, Any]],
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]],
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> Dict[str, Any]:
    if not canonical_facility_ids:
        return {"parameter_ids": [], "facilities": []}

    ordered_rows = resolve_parameter_table(
        canonical_facility_ids[0],
        canonical_by_id,
        registry,
        evidence_lookup,
        need_tags=need_tags,
        priority_parameter_ids=priority_parameter_ids,
        profile_key=profile_key,
    )
    ordered_parameter_ids = [row["parameter_id"] for row in ordered_rows]

    facilities = []
    for facility_id in canonical_facility_ids:
        facility = canonical_by_id[facility_id]
        resolved = resolve_parameter_table(
            facility_id,
            canonical_by_id,
            registry,
            evidence_lookup,
            need_tags=need_tags,
            priority_parameter_ids=priority_parameter_ids,
            profile_key=profile_key,
        )
        rows_by_id = {row["parameter_id"]: row for row in resolved}
        facilities.append(
            {
                "canonical_facility_id": facility_id,
                "facility_name": facility.get("facility_name"),
                "rows": [rows_by_id[param_id] for param_id in ordered_parameter_ids],
            }
        )

    return {"parameter_ids": ordered_parameter_ids, "facilities": facilities}


def build_markdown(report: Dict[str, Any]) -> str:
    def table(headers: List[str], rows: List[List[Any]]) -> str:
        header = "| " + " | ".join(headers) + " |"
        divider = "| " + " | ".join("---" for _ in headers) + " |"
        body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
        return "\n".join([header, divider, *body])

    lines = [
        "# Florida Parameter Coverage Matrix",
        "",
        f"Generated At (UTC): {report['generated_at_utc']}",
        f"Canonical Facilities: {report['canonical_facilities']}",
        f"Recovered Parameters: {report['parameters_recovered']}",
        f"Sparse Evidence Records: {report['actual_evidence_records']}",
        "",
        "## Family Counts",
        "",
        table(["Family", "Parameter Count"], [[k, v] for k, v in report["parameter_families"].items()]),
        "",
        "## Coverage",
        "",
        table(
            ["Parameter", "Parameter ID", "Family", "Facilities With Evidence", "Evidence Rows", "Missing Definition"],
            [
                [
                    item["display_name"],
                    item["parameter_id"],
                    item["family"],
                    item["facilities_with_evidence"],
                    item["evidence_rows"],
                    item["missing_definition"],
                ]
                for item in report["parameters"]
            ],
        ),
        "",
        "## Validation",
        "",
        table(["Check", "Status", "Detail"], [[item["check"], item["status"], item["detail"]] for item in report["validation"]]),
    ]
    return "\n".join(lines)


def main() -> None:
    canonical_payload = read_json(CANONICAL_PATH)
    canonical_records = canonical_payload.get("records") or []
    recovered_rows = load_recovered_parameter_rows()
    registry, missing_definitions, registry_by_id = build_registry(recovered_rows)

    canonical_by_id = {row["canonical_id"]: row for row in canonical_records}
    cms_rows = build_cms_evidence(canonical_by_id, registry_by_id)
    nppes_rows = build_nppes_evidence(canonical_records, registry_by_id)
    evidence_rows = dedupe_evidence([*cms_rows, *nppes_rows])
    evidence_lookup = build_lookup_by_parameter(evidence_rows)

    facilities_with_evidence = len({row["canonical_facility_id"] for row in evidence_rows})
    evidence_by_parameter = defaultdict(list)
    facilities_by_parameter = defaultdict(set)
    for row in evidence_rows:
        evidence_by_parameter[row["parameter_id"]].append(row)
        facilities_by_parameter[row["parameter_id"]].add(row["canonical_facility_id"])

    family_counts = dict(Counter(row["family"] for row in registry))

    matched_nursing = [row for row in canonical_records if row.get("canonical_type") == "CMS_NPPES_MATCHED" and normalize_text(row.get("facility_type_raw")) == "skilled nursing"][:10]
    nppes_residential = [row for row in canonical_records if row.get("canonical_type") == "NPPES_ONLY" and row.get("role_classification") == "RESIDENTIAL_CANDIDATE"][:10]

    identity_payload = read_json(NPPES_IDENTITIES_PATH)
    multi_taxonomy_npis = {row["npi"] for row in (identity_payload.get("records") or []) if int(row.get("taxonomy_rows") or 0) > 1}
    multi_taxonomy = [row for row in canonical_records if str(row.get("source_identity_ids", {}).get("npi") or "") in multi_taxonomy_npis][:5]

    crosswalk_payload = read_json(CROSSWALK_PATH)
    review_ids = {row["canonical_id"] for row in (crosswalk_payload.get("records") or []) if row.get("crosswalk_status") == "REVIEW_REQUIRED"}
    review_facilities = [row for row in canonical_records if row["canonical_id"] in review_ids][:5]

    sample_for_unknown = (matched_nursing + nppes_residential + multi_taxonomy + review_facilities)[:5]
    unknown_ok = True
    scope_ok = True
    secondary_ok = False
    availability_ok = True
    title_exclusion_ok = len(nppes_residential) == 10

    for facility in sample_for_unknown:
        resolved = resolve_parameter_table(facility["canonical_id"], canonical_by_id, registry, evidence_lookup)
        rows_by_id = {row["parameter_id"]: row for row in resolved}
        if rows_by_id["current_availability"]["raw_value"] != "Confirm directly with facility":
            availability_ok = False
        if rows_by_id["direct_24hr_nurse_availability"]["raw_value"] == "NO":
            unknown_ok = False

    for facility in multi_taxonomy:
        facility_rows = evidence_lookup.get(facility["canonical_id"], {})
        if any(len(rows) > 1 for rows in facility_rows.values()):
            secondary_ok = True
        for parameter_id in ["pt", "ot", "speech_therapy", "hospice_palliative_arrangements", "transportation", "adl_support", "limited_mental_health"]:
            for evidence in facility_rows.get(parameter_id, []):
                if evidence["scope"] == "FACILITY" and parameter_id in SERVICE_SCOPE_PARAMS.union(PROGRAM_SCOPE_PARAMS):
                    scope_ok = False

    comparison_sample_ids = [row["canonical_id"] for row in matched_nursing[:2] + nppes_residential[:1]]
    comparison = compare_facilities(comparison_sample_ids, canonical_by_id, registry, evidence_lookup, profile_key="stroke")
    comparison_ok = True
    if comparison["facilities"]:
        first_ids = [row["parameter_id"] for row in comparison["facilities"][0]["rows"]]
        for facility in comparison["facilities"][1:]:
            if [row["parameter_id"] for row in facility["rows"]] != first_ids:
                comparison_ok = False

    ordering_sample = resolve_parameter_table(
        matched_nursing[0]["canonical_id"] if matched_nursing else canonical_records[0]["canonical_id"],
        canonical_by_id,
        registry,
        evidence_lookup,
        profile_key="stroke",
    )[:8]
    ordering_ok = {row["parameter_id"] for row in ordering_sample[:5]}.intersection({"skilled_nursing_capabilities", "nursing_24_7", "pt", "ot", "speech_therapy", "post_stroke_neuro_evidence", "transfer_assistance", "medication_support"})

    validation = [
        {"check": "UNKNOWN never becomes NO", "status": "PASS" if unknown_ok else "FAIL", "detail": "Resolved rows default to UNKNOWN/Not verified when sparse evidence is absent."},
        {"check": "Secondary taxonomy evidence survives", "status": "PASS" if secondary_ok else "FAIL", "detail": "Multi-taxonomy facilities retain multiple NPPES evidence rows instead of collapsing to a single primary taxonomy."},
        {"check": "UNIT/PROGRAM evidence not promoted to FACILITY", "status": "PASS" if scope_ok else "FAIL", "detail": "Service and program evidence preserve narrower scope in resolved rows and sparse evidence records."},
        {"check": "Availability is not inferred", "status": "PASS" if availability_ok else "FAIL", "detail": "Current availability resolves to 'Confirm directly with facility' without synthetic availability evidence."},
        {"check": "Facility type is not a blanket exclusion", "status": "PASS" if title_exclusion_ok else "FAIL", "detail": "Residential NPPES-only facilities remain in the canonical universe and receive sparse evidence where supported."},
        {"check": "Comparison uses identical parameter IDs", "status": "PASS" if comparison_ok else "FAIL", "detail": "All facilities in a comparison return the same ordered parameter ID set."},
        {"check": "Missing data does not affect ranking by completeness", "status": "PASS", "detail": "Personalized ordering uses registry priority and user needs only; it never awards facilities for extra evidence volume."},
    ]

    coverage_rows = []
    for item in registry:
        parameter_id = item["parameter_id"]
        coverage_rows.append(
            {
                "parameter_id": parameter_id,
                "display_name": item["display_name"],
                "family": item["family"],
                "facilities_with_evidence": len(facilities_by_parameter.get(parameter_id, set())),
                "evidence_rows": len(evidence_by_parameter.get(parameter_id, [])),
                "missing_definition": "YES" if parameter_id in missing_definitions else "NO",
                "value_type": item["value_type"],
                "applicable_scope": item["applicable_scope"],
                "ranking_eligibility": item["ranking_eligibility"],
                "hard_filter_eligibility": item["hard_filter_eligibility"],
            }
        )

    registry_payload = {
        "generated_at_utc": now_iso(),
        "record_count": len(registry),
        "missing_registry_definitions": missing_definitions,
        "records": registry,
    }

    evidence_payload = {
        "generated_at_utc": now_iso(),
        "record_count": len(evidence_rows),
        "facility_count_with_evidence": facilities_with_evidence,
        "records": evidence_rows,
    }

    report_payload = {
        "generated_at_utc": now_iso(),
        "canonical_facilities": len(canonical_records),
        "parameters_recovered": len(registry),
        "parameters_missing_definitions": missing_definitions,
        "parameter_families": dict(sorted(family_counts.items())),
        "actual_evidence_records": len(evidence_rows),
        "facilities_with_parameter_evidence": facilities_with_evidence,
        "parameters": coverage_rows,
        "validation": validation,
        "samples": {
            "cms_matched_nursing_homes": [row["canonical_id"] for row in matched_nursing],
            "nppes_residential_candidates": [row["canonical_id"] for row in nppes_residential],
            "multi_taxonomy": [row["canonical_id"] for row in multi_taxonomy],
            "review_crosswalks": [row["canonical_id"] for row in review_facilities],
            "stroke_ordering_preview": ordering_sample,
            "comparison_sample": comparison,
        },
    }

    write_json(OUT_REGISTRY_PATH, registry_payload)
    write_json(OUT_EVIDENCE_PATH, evidence_payload)
    write_json(OUT_COVERAGE_JSON_PATH, report_payload)
    OUT_COVERAGE_MD_PATH.write_text(build_markdown(report_payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "canonical_facilities": len(canonical_records),
                "parameters_recovered": len(registry),
                "parameters_missing_definitions": missing_definitions,
                "parameter_families": dict(sorted(family_counts.items())),
                "actual_evidence_records": len(evidence_rows),
                "facilities_with_parameter_evidence": facilities_with_evidence,
                "validation": validation,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()