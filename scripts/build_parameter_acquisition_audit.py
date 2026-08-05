from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "database" / "optime_parameter_registry.json"
COVERAGE_PATH = ROOT / "reports" / "FLORIDA_PARAMETER_COVERAGE_MATRIX.json"
EVIDENCE_PATH = ROOT / "database" / "florida_facility_parameter_evidence.json"
FACILITIES_PATH = ROOT / "database" / "florida_facility_universe_canonical.json"
REPORTS = ROOT / "reports"
ADMIN_DATA_PATH = ROOT / "frontend" / "src" / "data" / "parameter-acquisition-audit.json"

ACQUISITION_CLASSES = {
    "GOVERNMENT_AUTOMATIC",
    "FACILITY_WEBSITE_AUTOMATIC",
    "FACILITY_DOCUMENT_AUTOMATIC",
    "THIRD_PARTY_INTERNET_AUTOMATIC",
    "DIRECT_FACILITY_REQUEST",
    "MANUAL_RESEARCH",
    "HUMAN_VERIFICATION",
    "NOT_RELIABLY_AVAILABLE",
}

OWNERS = {
    "AUTOMATED_PIPELINE",
    "DATA_RESEARCH_TEAM",
    "FACILITY_RELATIONS",
    "CLINICAL_REVIEWER",
    "COMPLIANCE_REVIEWER",
    "FACILITY_SELF_SERVICE",
    "FAMILY_FEEDBACK",
    "NOT_ASSIGNED",
}

GOVERNMENT = {
    "skilled_nursing_capabilities", "nursing_24_7", "rn_hours_per_resident_day",
    "total_nurse_hours_per_resident_day", "specialty_licenses", "extended_congregate_care",
    "limited_nursing_services", "limited_mental_health", "inspection_rating", "deficiency_count",
    "deficiency_severity", "complaint_related_findings", "fire_safety_deficiencies",
    "infection_control_findings", "penalties_fines", "sanctions_final_orders", "payment_denials",
    "quality_measures", "hospital_claims_outcomes", "staffing_turnover", "medicaid_attributes",
    "medicare_attributes",
}

FACILITY_WEBSITE = {
    "pt", "ot", "speech_therapy", "short_term_rehab", "memory_care", "dementia_alz_programs",
    "wound_care", "hospice_palliative_arrangements", "transportation", "amenities",
    "private_shared_rooms", "accessibility", "published_rates",
}

FACILITY_DOCUMENT = {
    "dietary_capabilities", "gluten_free", "kosher", "activities", "payer_information",
}

DIRECT_REQUEST = {
    "direct_24hr_nurse_availability", "third_party_24hr_nurse_availability", "adl_support",
    "medication_support", "transfer_assistance", "therapy_staffing", "dialysis_arrangements",
    "secured_units", "languages", "fees", "current_availability", "earliest_admission_date",
    "waiting_list", "current_price", "current_promotions",
}

HUMAN_REVIEW = {
    "higher_acuity_capabilities", "post_stroke_neuro_evidence", "respiratory_trach_vent",
}

MANUAL = {"religious_cultural_services"}

THIRD_PARTY = set()
NOT_RELIABLE = set()
MEDIA_USEFUL = {"activities", "amenities", "private_shared_rooms", "accessibility"}

CLASS_BY_ID = {
    **{item: "GOVERNMENT_AUTOMATIC" for item in GOVERNMENT},
    **{item: "FACILITY_WEBSITE_AUTOMATIC" for item in FACILITY_WEBSITE},
    **{item: "FACILITY_DOCUMENT_AUTOMATIC" for item in FACILITY_DOCUMENT},
    **{item: "DIRECT_FACILITY_REQUEST" for item in DIRECT_REQUEST},
    **{item: "HUMAN_VERIFICATION" for item in HUMAN_REVIEW},
    **{item: "MANUAL_RESEARCH" for item in MANUAL},
    **{item: "THIRD_PARTY_INTERNET_AUTOMATIC" for item in THIRD_PARTY},
    **{item: "NOT_RELIABLY_AVAILABLE" for item in NOT_RELIABLE},
}

CATEGORY_BY_ID = {
    **{item: "6. Nursing and staffing" for item in {
        "skilled_nursing_capabilities", "nursing_24_7", "direct_24hr_nurse_availability",
        "third_party_24hr_nurse_availability", "rn_hours_per_resident_day",
        "total_nurse_hours_per_resident_day", "adl_support", "medication_support",
        "transfer_assistance", "higher_acuity_capabilities", "staffing_turnover",
    }},
    **{item: "5. Rehabilitation" for item in {
        "pt", "ot", "speech_therapy", "short_term_rehab", "post_stroke_neuro_evidence",
        "therapy_staffing",
    }},
    **{item: "4. Care capabilities" for item in {
        "memory_care", "dementia_alz_programs", "wound_care", "dialysis_arrangements",
        "respiratory_trach_vent", "hospice_palliative_arrangements", "specialty_licenses",
        "extended_congregate_care", "limited_nursing_services", "limited_mental_health", "secured_units",
    }},
    **{item: "7. Quality and outcomes" for item in {
        "quality_measures", "hospital_claims_outcomes",
    }},
    **{item: "8. Inspections and enforcement" for item in {
        "inspection_rating", "deficiency_count", "deficiency_severity", "complaint_related_findings",
        "fire_safety_deficiencies", "infection_control_findings", "penalties_fines",
        "sanctions_final_orders", "payment_denials",
    }},
    **{item: "11. Language and culture" for item in {"languages", "religious_cultural_services"}},
    **{item: "12. Dietary needs" for item in {"dietary_capabilities", "gluten_free", "kosher"}},
    **{item: "13. Amenities and lifestyle" for item in {
        "activities", "transportation", "amenities", "private_shared_rooms", "accessibility",
    }},
    **{item: "9. Pricing and payment" for item in {
        "payer_information", "medicaid_attributes", "medicare_attributes", "published_rates", "fees",
        "current_price", "current_promotions",
    }},
    **{item: "10. Availability and admissions" for item in {
        "current_availability", "earliest_admission_date", "waiting_list",
    }},
}

DEPARTMENT_BY_ID = {
    **{item: ("Admissions", "Admissions Director") for item in {
        "payer_information", "published_rates", "fees", "current_availability",
        "earliest_admission_date", "waiting_list", "current_price", "current_promotions",
        "private_shared_rooms",
    }},
    **{item: ("Nursing", "Director of Nursing") for item in {
        "skilled_nursing_capabilities", "nursing_24_7", "direct_24hr_nurse_availability",
        "third_party_24hr_nurse_availability", "adl_support", "medication_support", "transfer_assistance",
        "higher_acuity_capabilities", "wound_care", "dialysis_arrangements", "respiratory_trach_vent",
        "hospice_palliative_arrangements", "secured_units",
    }},
    **{item: ("Rehabilitation", "Rehabilitation Director") for item in {
        "pt", "ot", "speech_therapy", "short_term_rehab", "post_stroke_neuro_evidence", "therapy_staffing",
    }},
    **{item: ("Dietary", "Dietary Services Director") for item in {
        "dietary_capabilities", "gluten_free", "kosher",
    }},
    **{item: ("Activities", "Activities Director") for item in {
        "activities", "religious_cultural_services", "transportation", "amenities",
    }},
    **{item: ("Administration / HR", "Administrator or HR Director") for item in {
        "languages", "accessibility", "specialty_licenses", "extended_congregate_care",
        "limited_nursing_services", "limited_mental_health",
    }},
}

GOLDEN_IDS = [
    "CMS-105719", "CMS-105460", "CMS-105664", "CMS-106149", "CMS-106066",
    "CMS-105571", "CMS-105193", "CMS-105638", "CMS-105434", "CMS-106046",
]

MEDIA_TYPES = [
    ("exterior photo", "Official facility website or facility-supplied file", "Identity match plus visible exterior/address cues", "Neutral photo-pending placeholder"),
    ("entrance", "Official facility website or facility-supplied file", "Entrance signage matched to canonical identity", "Do not substitute a generic entrance"),
    ("lobby", "Official facility website or facility-supplied file", "Page context and facility identity anchors", "Text-only availability state"),
    ("resident room", "Official facility gallery or facility-supplied file", "Room type and facility attestation", "Room photo unavailable"),
    ("bathroom", "Facility-supplied file", "Facility attestation and accessibility context", "Bathroom photo unavailable"),
    ("dining room", "Official facility gallery or facility-supplied file", "Facility identity and dining-area context", "Dining photo unavailable"),
    ("therapy gym", "Official rehabilitation page or facility-supplied file", "Facility identity and equipment/context review", "Therapy photo unavailable"),
    ("activity area", "Official gallery/calendar or facility-supplied file", "Facility identity and activity-space review", "Activity photo unavailable"),
    ("outdoor space", "Official gallery or facility-supplied file", "Geographic and facility identity match", "Outdoor photo unavailable"),
    ("floor plan", "Official facility PDF/page", "Address/community/room-type match", "Floor plan unavailable"),
    ("menu", "Official current PDF or facility-supplied file", "Document date and facility identity", "Menu awaiting confirmation"),
    ("activity calendar", "Official current PDF or facility-supplied file", "Document month and facility identity", "Calendar awaiting confirmation"),
    ("brochure", "Official facility PDF or facility-supplied file", "Facility identity and publication date", "Brochure unavailable"),
    ("video tour", "Official facility account or facility-supplied file", "Account ownership and facility identity", "Video tour unavailable"),
    ("map", "Licensed map provider embed/API", "Canonical coordinates and address match", "Address-only map fallback"),
    ("street view", "Licensed street-view provider embed/API", "Canonical coordinates and provider terms", "Map fallback; never cache imagery without license"),
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def source_profile(parameter_id: str, acquisition_class: str) -> tuple[str, str, str]:
    if acquisition_class == "GOVERNMENT_AUTOMATIC":
        if parameter_id in {"specialty_licenses", "extended_congregate_care", "limited_nursing_services", "limited_mental_health", "sanctions_final_orders"}:
            return "Florida AHCA licensing/enforcement records", "A", "AHCA open data, license lookup, and final-order documents"
        return "CMS Care Compare downloadable datasets", "A", "CMS Provider Information, staffing, inspections, penalties, and quality files"
    if acquisition_class == "FACILITY_WEBSITE_AUTOMATIC":
        return "Official facility website", "B", "Official service pages, structured data, and facility-owned media"
    if acquisition_class == "FACILITY_DOCUMENT_AUTOMATIC":
        return "Official facility document", "B", "Current facility PDF, menu, calendar, policy, brochure, or payer sheet"
    if acquisition_class == "DIRECT_FACILITY_REQUEST":
        return "Direct facility response", "B", "Named staff response plus current supporting document when available"
    if acquisition_class == "HUMAN_VERIFICATION":
        return "Official clinical program material", "B", "Independent professional or institutional evidence (Authority C), reviewed by a qualified clinician"
    if acquisition_class == "MANUAL_RESEARCH":
        return "Official and institutional public sources", "B/C", "Manual cross-source research with recorded provenance"
    if acquisition_class == "THIRD_PARTY_INTERNET_AUTOMATIC":
        return "Independent professional source", "C", "Institutional directory or professional source; never reviews as fact"
    return "No reliable current source", "F", "Remain UNKNOWN until a governed source becomes available"


def acquisition_flags(parameter_id: str, acquisition_class: str) -> dict[str, str]:
    return {
        "Government source available": yes_no(acquisition_class == "GOVERNMENT_AUTOMATIC"),
        "Facility website source available": yes_no(acquisition_class in {"FACILITY_WEBSITE_AUTOMATIC", "FACILITY_DOCUMENT_AUTOMATIC"}),
        "Public internet source available": yes_no(acquisition_class in {"GOVERNMENT_AUTOMATIC", "FACILITY_WEBSITE_AUTOMATIC", "FACILITY_DOCUMENT_AUTOMATIC", "THIRD_PARTY_INTERNET_AUTOMATIC", "MANUAL_RESEARCH"}),
        "Direct facility confirmation required": yes_no(acquisition_class == "DIRECT_FACILITY_REQUEST"),
        "Manual research required": yes_no(acquisition_class == "MANUAL_RESEARCH"),
        "Automatic extraction possible": yes_no(acquisition_class in {"GOVERNMENT_AUTOMATIC", "FACILITY_WEBSITE_AUTOMATIC", "FACILITY_DOCUMENT_AUTOMATIC", "THIRD_PARTY_INTERNET_AUTOMATIC"}),
        "API available": yes_no(acquisition_class == "GOVERNMENT_AUTOMATIC"),
        "Scraping required": yes_no(acquisition_class in {"FACILITY_WEBSITE_AUTOMATIC", "THIRD_PARTY_INTERNET_AUTOMATIC"}),
        "Document/PDF extraction required": yes_no(acquisition_class in {"FACILITY_DOCUMENT_AUTOMATIC", "HUMAN_VERIFICATION"}),
        "Image analysis useful": yes_no(parameter_id in MEDIA_USEFUL),
        "Human verification required": yes_no(acquisition_class in {"DIRECT_FACILITY_REQUEST", "MANUAL_RESEARCH", "HUMAN_VERIFICATION", "NOT_RELIABLY_AVAILABLE"}),
    }


def refresh_profile(parameter_id: str, acquisition_class: str) -> tuple[str, str, str]:
    if parameter_id in {"current_availability", "earliest_admission_date", "waiting_list", "current_price", "current_promotions"}:
        return "On demand and every 7 days while active", "0-7 days", "LOW until facility confirms"
    if parameter_id in {"published_rates", "fees", "payer_information"}:
        return "Monthly and on document change", "0-30 days", "MEDIUM"
    if acquisition_class == "GOVERNMENT_AUTOMATIC":
        return "On source release; check monthly", "Source publication lag, usually 1-12 months", "HIGH for covered regulated facilities"
    if acquisition_class in {"FACILITY_WEBSITE_AUTOMATIC", "FACILITY_DOCUMENT_AUTOMATIC"}:
        return "Monthly crawl; invalidate on page/document change", "0-30 days after observed change", "MEDIUM"
    if acquisition_class == "DIRECT_FACILITY_REQUEST":
        return "Quarterly; sooner for case-active requests", "0-90 days", "MEDIUM after response"
    return "Annual review and event-triggered refresh", "0-12 months", "LOW to MEDIUM"


def owner_profile(acquisition_class: str) -> tuple[str, str]:
    if acquisition_class in {"GOVERNMENT_AUTOMATIC", "FACILITY_WEBSITE_AUTOMATIC", "FACILITY_DOCUMENT_AUTOMATIC", "THIRD_PARTY_INTERNET_AUTOMATIC"}:
        return "AUTOMATED_PIPELINE", "DATA_RESEARCH_TEAM"
    if acquisition_class == "DIRECT_FACILITY_REQUEST":
        return "FACILITY_RELATIONS", "DATA_RESEARCH_TEAM"
    if acquisition_class == "HUMAN_VERIFICATION":
        return "CLINICAL_REVIEWER", "CLINICAL_REVIEWER"
    if acquisition_class == "MANUAL_RESEARCH":
        return "DATA_RESEARCH_TEAM", "COMPLIANCE_REVIEWER"
    return "NOT_ASSIGNED", "COMPLIANCE_REVIEWER"


def question_for(parameter: dict[str, Any]) -> str:
    name = parameter["display_name"]
    value_type = parameter["value_type"]
    if value_type == "BOOLEAN_STATUS":
        return f"Does this facility currently provide {name.lower()}? Please answer Yes or No and identify the applicable facility, unit, program, or service line."
    return f"What is the current value for {name.lower()}? Please provide the effective date and applicable scope."


def build_rows(registry: list[dict[str, Any]], coverage: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage_by_id = {row["parameter_id"]: row for row in coverage["parameters"]}
    current_sources: dict[str, set[str]] = defaultdict(set)
    for evidence_row in evidence:
        source = str(evidence_row.get("source") or "").strip()
        if source:
            current_sources[evidence_row["parameter_id"]].add(source)
    total_facilities = int(coverage["canonical_facilities"])
    rows = []
    for parameter in registry:
        parameter_id = parameter["parameter_id"]
        acquisition_class = CLASS_BY_ID[parameter_id]
        coverage_row = coverage_by_id[parameter_id]
        preferred_source, authority, alternatives = source_profile(parameter_id, acquisition_class)
        refresh, freshness, reliability = refresh_profile(parameter_id, acquisition_class)
        owner, approver = owner_profile(acquisition_class)
        covered = int(coverage_row["facilities_with_evidence"])
        coverage_percent = round(100 * covered / total_facilities, 1)
        criticality = "CRITICAL" if parameter["hard_filter_eligibility"] else "HIGH" if parameter["ranking_eligibility"] else "STANDARD"
        implementation = "IMPLEMENTED_WITH_COVERAGE" if covered else "DEFINED_NO_CURRENT_COVERAGE"
        flags = acquisition_flags(parameter_id, acquisition_class)
        row = {
            "Parameter ID": parameter_id,
            "Display name": parameter["display_name"],
            "Category": CATEGORY_BY_ID[parameter_id],
            "Exact meaning": parameter["consumer_description"],
            "Allowed values": " | ".join(parameter["allowed_values"]) if parameter.get("allowed_values") else parameter["value_type"],
            "Why the parameter matters": f"Supports case-specific evaluation of {parameter['display_name'].lower()} at {parameter['applicable_scope'].lower()} scope.",
            "Used in eligibility": yes_no(bool(parameter["hard_filter_eligibility"])),
            "Used in ranking": yes_no(bool(parameter["ranking_eligibility"])),
            "Criticality": criticality,
            "Primary acquisition class": acquisition_class,
            "Preferred source": preferred_source,
            "Source authority": authority,
            "Alternative sources": alternatives,
            **flags,
            "Refresh frequency": refresh,
            "Expected data freshness": freshness,
            "Expected facility coverage": reliability,
            "Reliability level": authority,
            "Legal/copyright/access limitations": "Observe source terms, robots directives, rate limits, document licenses, and retention rules; public access does not imply republication rights.",
            "Current OPTIME coverage": f"{covered}/{total_facilities} facilities ({coverage_percent}%)",
            "Current coverage count": covered,
            "Current coverage percent": coverage_percent,
            "Current implementation status": implementation,
            "Current source mappings": " | ".join(sorted(current_sources[parameter_id])) or "No current evidence source mapping",
            "Registry source priority": " | ".join(parameter.get("source_priority") or []),
            "Registry freshness rule": parameter["freshness_rule"],
            "Recommended acquisition method": f"Acquire from {preferred_source}; preserve raw source, scope, retrieval date, and evidence authority before normalization.",
            "Recommended ACTION when missing": "Keep UNKNOWN; queue " + ("facility request" if acquisition_class == "DIRECT_FACILITY_REQUEST" else "source refresh/research") + "; never convert absence into NO.",
            "Recommended recipient at facility": " / ".join(DEPARTMENT_BY_ID.get(parameter_id, ("Administration", "Facility Administrator"))),
            "Required evidence standard": "Authority A source record" if authority == "A" else "Authority B signed response/document or corroborated source evidence",
            "Can facility response become VERIFIED automatically": "NO",
            "Operational owner": owner,
            "Final value approver": approver,
            "Notes": "Facility claims remain CLAIMED_BY_FACILITY until documentary support and scope/freshness checks pass. UNKNOWN remains neutral.",
        }
        rows.append(row)
    return rows


def validate(registry: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    registry_ids = [row["parameter_id"] for row in registry]
    row_ids = [row["Parameter ID"] for row in rows]
    if len(registry_ids) != 59 or len(set(registry_ids)) != 59:
        raise ValueError(f"Expected exactly 59 unique canonical parameters, found {len(set(registry_ids))}")
    if set(registry_ids) != set(CLASS_BY_ID):
        missing = sorted(set(registry_ids) - set(CLASS_BY_ID))
        extra = sorted(set(CLASS_BY_ID) - set(registry_ids))
        raise ValueError(f"Acquisition classification mismatch; missing={missing}, extra={extra}")
    if row_ids != registry_ids:
        raise ValueError("Generated row order or IDs differ from canonical registry")
    if any(row["Primary acquisition class"] not in ACQUISITION_CLASSES for row in rows):
        raise ValueError("Invalid acquisition class")
    if any(row["Operational owner"] not in OWNERS for row in rows):
        raise ValueError("Invalid operational owner")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = columns or list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def priority_lists(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hardest_order = [
        "current_availability", "current_price", "earliest_admission_date", "waiting_list",
        "post_stroke_neuro_evidence", "respiratory_trach_vent", "higher_acuity_capabilities",
        "therapy_staffing", "direct_24hr_nurse_availability", "third_party_24hr_nurse_availability",
    ]
    easiest_order = [
        "inspection_rating", "deficiency_count", "deficiency_severity", "complaint_related_findings",
        "fire_safety_deficiencies", "infection_control_findings", "penalties_fines", "payment_denials",
        "rn_hours_per_resident_day", "total_nurse_hours_per_resident_day",
    ]
    by_id = {row["Parameter ID"]: row for row in rows}
    return [by_id[item] for item in hardest_order], [by_id[item] for item in easiest_order]


def write_matrix_markdown(rows: list[dict[str, Any]], counts: Counter[str], generated_at: str) -> None:
    category_counts = Counter(row["Category"] for row in rows)
    hardest, easiest = priority_lists(rows)
    lines = [
        "# OPTIME Parameter Acquisition Matrix",
        "",
        f"Generated: {generated_at}",
        "",
        "Canonical source of truth: `database/optime_parameter_registry.json` (59 parameters). This audit does not add parameters or alter ranking/evidence semantics.",
        "",
        "## Acquisition Summary",
        "",
        markdown_table(["Primary class", "Count"], [[key, counts.get(key, 0)] for key in sorted(ACQUISITION_CLASSES)]),
        "",
        "## Practical Categories",
        "",
        markdown_table(["Category", "Canonical parameter count"], [[key, category_counts.get(key, 0)] for key in [f"{index}. {name}" for index, name in enumerate([
            "Identity and licensing", "Ownership and organization", "Capacity and occupancy", "Care capabilities", "Rehabilitation", "Nursing and staffing", "Quality and outcomes", "Inspections and enforcement", "Pricing and payment", "Availability and admissions", "Language and culture", "Dietary needs", "Amenities and lifestyle", "Resident experience and reviews", "Location and practical access", "Media and photos", "Documents and downloadable materials", "Legal and reputation", "OPTIME proprietary intelligence",
        ], 1)]]),
        "",
        "> Zero-count categories are intentional: those concepts are not canonical parameters in the current 59-parameter registry and were not invented for this audit.",
        "",
        "## Top 10 Hardest Parameters", "",
        markdown_table(["Parameter", "Primary class", "Reason"], [[row["Display name"], row["Primary acquisition class"], "Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response"] for row in hardest]),
        "",
        "## Top 10 Easiest High-Value Parameters", "",
        markdown_table(["Parameter", "Primary class", "Reason"], [[row["Display name"], row["Primary acquisition class"], "Authoritative structured government source and direct decision relevance"] for row in easiest]),
        "",
        "## Parameter-by-Parameter Audit",
        "",
        markdown_table(
            ["ID", "Display name", "Category", "Class", "Authority", "Eligibility", "Ranking", "Current coverage", "Owner", "Missing action"],
            [[row["Parameter ID"], row["Display name"], row["Category"], row["Primary acquisition class"], row["Source authority"], row["Used in eligibility"], row["Used in ranking"], row["Current OPTIME coverage"], row["Operational owner"], row["Recommended ACTION when missing"]] for row in rows],
        ),
        "",
        "The CSV is the exhaustive field-level matrix. The JSON source map preserves the same rows as structured records.",
    ]
    (REPORTS / "OPTIME_PARAMETER_ACQUISITION_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def request_rows(rows: list[dict[str, Any]], registry_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row["Primary acquisition class"] not in {"DIRECT_FACILITY_REQUEST", "HUMAN_VERIFICATION"}:
            continue
        parameter = registry_by_id[row["Parameter ID"]]
        department, role = DEPARTMENT_BY_ID.get(row["Parameter ID"], ("Administration", "Facility Administrator"))
        output.append({
            "Parameter ID": row["Parameter ID"],
            "Display name": row["Display name"],
            "Recipient department": department,
            "Recipient role": role,
            "Exact question": question_for(parameter),
            "Expected answer type": row["Allowed values"],
            "Supporting document requested": f"Current policy, schedule, license, service description, rate sheet, or signed attestation supporting {row['Display name'].lower()}",
            "Priority": row["Criticality"],
            "Response expiry": "7 days" if row["Parameter ID"] in {"current_availability", "earliest_admission_date", "waiting_list", "current_price", "current_promotions"} else "90 days",
            "Follow-up cadence": "Day 3, day 7, then close as UNKNOWN on day 14",
            "Response evidence state": "CLAIMED_BY_FACILITY",
            "Upgrade to VERIFIED": "Named respondent, timestamp, exact scope, and supporting Authority B document; clinical claims additionally require clinical reviewer approval.",
        })
    return output


def write_media_policy(generated_at: str) -> None:
    rows = []
    for media_type, source, verification, fallback in MEDIA_TYPES:
        is_map = media_type in {"map", "street view"}
        rows.append([
            media_type, source,
            "Only with facility ownership, explicit license, public-domain status, or provider embed terms",
            "Only when provider/host terms expressly permit it",
            "Only with documented license/permission" if not is_map else "No, unless provider terms expressly permit caching",
            "As required by license/provider terms",
            "YES when rights are unclear",
            verification, fallback,
        ])
    content = [
        "# OPTIME Media Acquisition Policy", "", f"Generated: {generated_at}", "",
        "Media is supplementary evidence and is not a substitute for canonical care, quality, or availability evidence. Public accessibility does not establish display, reproduction, caching, or hotlinking rights.", "",
        markdown_table(["Media type", "Likely source", "Public display rights", "Hotlinking", "Caching", "Attribution", "Manual permission", "Verification", "Fallback"], rows), "",
        "## Mandatory Controls", "",
        "- Store source URL, rights basis, capture date, facility identity match, and reviewer decision.",
        "- Do not use review-platform, social-media, real-estate, news, or directory photos without a documented license.",
        "- Prefer facility-supplied originals under explicit OPTIME display permission over copied website assets.",
        "- Image analysis may classify scene type or detect identity anchors, but cannot establish ownership, rights, current condition, or clinical capability.",
        "- Remove or quarantine media when rights, identity, recency, or authenticity is disputed.",
    ]
    (REPORTS / "OPTIME_MEDIA_ACQUISITION_POLICY.md").write_text("\n".join(content) + "\n", encoding="utf-8")


def write_waves(rows: list[dict[str, Any]], generated_at: str) -> dict[str, int]:
    wave_by_class = {
        "GOVERNMENT_AUTOMATIC": 1,
        "FACILITY_WEBSITE_AUTOMATIC": 2,
        "FACILITY_DOCUMENT_AUTOMATIC": 2,
        "THIRD_PARTY_INTERNET_AUTOMATIC": 2,
        "DIRECT_FACILITY_REQUEST": 3,
        "MANUAL_RESEARCH": 4,
        "HUMAN_VERIFICATION": 4,
        "NOT_RELIABLY_AVAILABLE": 4,
    }
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row["Implementation wave"] = wave_by_class[row["Primary acquisition class"]]
        grouped[row["Implementation wave"]].append(row)
    coverage_targets = {1: 35, 2: 60, 3: 85, 4: 90}
    wave_meta = {
        1: ("High-value, easy, authoritative", "MEDIUM", "LOW", "CMS/AHCA connectors and identity crosswalk", "Publication lag and facility-type coverage gaps"),
        2: ("Facility website and document extraction", "HIGH", "MEDIUM", "Website discovery, robots/terms checks, PDF parser, source snapshots", "Website drift, access restrictions, and claim ambiguity"),
        3: ("Direct facility confirmation", "MEDIUM", "HIGH", "Question routing, contact management, claim state, expiry", "Low response rates and rapidly stale answers"),
        4: ("Manual and proprietary intelligence", "LOW engineering after tooling", "VERY HIGH", "Reviewer queues, compliance controls, outcome/feedback governance", "Cost, subjectivity, rights, and inconsistent evidence"),
    }
    lines = ["# OPTIME Parameter Implementation Waves", "", f"Generated: {generated_at}", ""]
    for wave in range(1, 5):
        title, engineering, operations, dependencies, risk = wave_meta[wave]
        wave_rows = grouped[wave]
        lines.extend([
            f"## Wave {wave} - {title}", "",
            f"- Parameter count: {len(wave_rows)}",
            f"- Engineering effort: {engineering}",
            f"- Operational effort: {operations}",
            f"- Expected cumulative profile coverage: approximately {coverage_targets[wave]}% for an applicable skilled-nursing pilot; actual coverage varies by facility type and parameter applicability.",
            f"- Expected ranking-confidence effect: {'High for governed covered factors' if wave == 1 else 'Incremental only where evidence is verified and case-relevant; generic completeness does not affect rank.'}",
            f"- Dependencies: {dependencies}",
            f"- Risk: {risk}",
            "- Parameters: " + ", ".join(row["Parameter ID"] for row in wave_rows), "",
        ])
    lines.extend(["## Guardrails", "", "Coverage targets are operational estimates, not measured pilot outcomes. UNKNOWN remains neutral, and no wave changes ranking logic or evidence authority."])
    (REPORTS / "OPTIME_PARAMETER_IMPLEMENTATION_WAVES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {f"wave_{wave}": len(grouped[wave]) for wave in range(1, 5)}


def write_golden_plan(rows: list[dict[str, Any]], facilities: list[dict[str, Any]], evidence: list[dict[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    facility_by_id = {row["canonical_id"]: row for row in facilities}
    evidence_ids: dict[str, set[str]] = defaultdict(set)
    for item in evidence:
        evidence_ids[item["canonical_facility_id"]].add(item["parameter_id"])
    pilot = []
    for canonical_id in GOLDEN_IDS:
        facility = facility_by_id.get(canonical_id)
        if not facility:
            raise ValueError(f"Golden facility missing from canonical universe: {canonical_id}")
        known = len(evidence_ids[canonical_id])
        pilot.append({
            "canonical_facility_id": canonical_id,
            "facility_name": facility["facility_name"],
            "city": facility.get("city"),
            "county": facility.get("county"),
            "known_parameters_at_baseline": known,
            "unknown_parameters_at_baseline": 59 - known,
            "target_known_or_actionable": 54,
        })
    lines = [
        "# OPTIME Golden 10 Facility Plan", "", f"Generated: {generated_at}", "",
        "Purpose: measure real acquisition coverage, operational cost, and refresh burden before any statewide expansion. Selection uses ten real canonical Florida facilities and does not imply recommendation quality or rank.", "",
        markdown_table(["Canonical ID", "Facility", "City", "County", "Known at baseline", "Unknown at baseline", "90% target"], [[item["canonical_facility_id"], item["facility_name"], item["city"], item["county"], item["known_parameters_at_baseline"], item["unknown_parameters_at_baseline"], item["target_known_or_actionable"]] for item in pilot]), "",
        "## Execution Per Facility", "",
        "1. Run CMS/AHCA and existing canonical automatic pipelines; retain raw source versions and retrieval timestamps.",
        "2. Crawl only the verified official facility domain, honoring terms and robots directives; extract service pages and current documents.",
        "3. Compute the 59-parameter known/unknown/actionable ledger. Applicability is recorded separately from missingness.",
        "4. Generate department-routed requests from the question bank for unresolved direct-confirmation parameters.",
        "5. Complete manual and clinical review queues; preserve CLAIMED_BY_FACILITY until verification requirements pass.",
        "6. Measure analyst minutes, facility-relations minutes, engineering exceptions, direct costs, elapsed days, response rate, evidence age, and verified completeness.",
        "7. Stop at 90% only when at least 54 applicable parameters are VERIFIED or have a documented governed resolution; do not manufacture completeness for non-applicable or unobtainable values.", "",
        "## Pilot Metrics", "",
        "- Cost per facility and cost per newly verified parameter",
        "- Calendar time and labor hours to 90% governed resolution",
        "- Automatic extraction precision and manual correction rate",
        "- Facility response rate by department and question",
        "- Coverage retained at 30, 90, 180, and 365 days",
        "- Source failure, access limitation, conflict, and expiry rates",
        "- Parameters that remain UNKNOWN despite full workflow",
        "",
        "## Planning Estimate", "",
        "Budget 6-10 hours of human work per facility for the first pilot cycle: 2-3 hours research/document review, 2-4 hours facility outreach/follow-up, and 2-3 hours clinical/compliance review. This is a hypothesis to measure, not a completed pilot result.",
    ]
    (REPORTS / "OPTIME_GOLDEN_10_FACILITY_PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pilot


def main() -> int:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    registry_payload = load_json(REGISTRY_PATH)
    coverage = load_json(COVERAGE_PATH)
    evidence_payload = load_json(EVIDENCE_PATH)
    facilities_payload = load_json(FACILITIES_PATH)
    registry = registry_payload["records"]
    rows = build_rows(registry, coverage, evidence_payload["records"])
    validate(registry, rows)
    counts = Counter(row["Primary acquisition class"] for row in rows)
    hardest, easiest = priority_lists(rows)
    registry_by_id = {row["parameter_id"]: row for row in registry}
    requests = request_rows(rows, registry_by_id)
    wave_counts = write_waves(rows, generated_at)
    pilot = write_golden_plan(rows, facilities_payload["records"], evidence_payload["records"], generated_at)

    write_csv(REPORTS / "OPTIME_PARAMETER_ACQUISITION_MATRIX.csv", rows)
    write_matrix_markdown(rows, counts, generated_at)
    source_map = {
        "generated_at_utc": generated_at,
        "canonical_registry": str(REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "parameter_count": len(rows),
        "acquisition_class_counts": dict(sorted(counts.items())),
        "source_authority_levels": {
            "A": "Official regulator or government dataset",
            "B": "Official facility source or signed facility document",
            "C": "Independent professional or institutional source",
            "D": "Public directory, review platform, social media, or aggregator",
            "E": "Inference from text, image, taxonomy, or indirect evidence",
            "F": "Unverified claim",
        },
        "wave_counts": wave_counts,
        "parameters_with_media_potential": sorted(MEDIA_USEFUL),
        "top_10_hardest": [row["Parameter ID"] for row in hardest],
        "top_10_easiest_high_value": [row["Parameter ID"] for row in easiest],
        "golden_facilities": pilot,
        "records": rows,
    }
    (REPORTS / "OPTIME_PARAMETER_SOURCE_MAP.json").write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")
    ADMIN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_DATA_PATH.write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")

    manual_rows = [{
        "Parameter ID": row["Parameter ID"], "Display name": row["Display name"],
        "Primary acquisition class": row["Primary acquisition class"], "Operational owner": row["Operational owner"],
        "Final value approver": row["Final value approver"], "Current implementation status": row["Current implementation status"],
        "Action when missing": row["Recommended ACTION when missing"], "Recipient": row["Recommended recipient at facility"],
        "Required evidence standard": row["Required evidence standard"], "Refresh frequency": row["Refresh frequency"],
    } for row in rows]
    write_csv(REPORTS / "OPTIME_MANUAL_DATA_ENTRY_MATRIX.csv", manual_rows)
    write_csv(REPORTS / "OPTIME_FACILITY_REQUEST_QUESTION_BANK.csv", requests)
    write_media_policy(generated_at)

    print(json.dumps({
        "parameters_audited": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "request_questions": len(requests),
        "golden_facilities": len(pilot),
        "wave_counts": wave_counts,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())