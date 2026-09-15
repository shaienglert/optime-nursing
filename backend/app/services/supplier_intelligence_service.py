from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "las_vegas_supplier_candidates.json"
PUBLIC_STATUSES = {"LIMITED", "VERIFIED"}
VALID_STATUSES = {"CANDIDATE", "LIMITED", "VERIFIED", "SUSPENDED", "CLOSED"}
VALID_INVOLVEMENT = {"DIRECT_LINK", "DIRECTORY", "PROFESSIONAL_REFERRAL", "OUTCOME_CRITICAL"}
CANONICAL_SECTORS = {
    "MOVE_MANAGEMENT", "MOVING_PACKING", "CONTENTS_EXIT", "CLEANING_SETUP",
    "PROPERTY_TRANSITION", "MOVE_TRANSPORT", "ROOM_RETAIL", "CONNECTIVITY",
    "DME_MOBILITY", "HOME_CARE", "PRIVATE_DUTY_NURSING", "HOME_HEALTH_THERAPY",
    "PHARMACY_MEDICATION", "ROUTINE_TRANSPORT", "SAFETY_MONITORING", "TECH_SUPPORT",
    "SENIOR_FITNESS", "COMPANIONSHIP", "MEALS_NUTRITION", "MOBILE_PERSONAL_HEALTH",
    "PERSONAL_CARE_LIFESTYLE", "PET_SUPPORT", "HOSPICE_PALLIATIVE",
    "GROCERY_DELIVERY", "HOME_MODIFICATION", "ELDER_LAW", "ESTATE_PLANNING",
    "GUARDIANSHIP", "MEDICAID_PLANNING", "MEDICARE_ADVISORY",
    "MEDICARE_INSURANCE_ADVISOR", "FIDUCIARY_FINANCIAL_PLANNING",
    "GERIATRIC_CARE_MANAGEMENT", "PATIENT_ADVOCACY", "PROFESSIONAL_GUARDIAN",
    "THERAPY_REHAB", "HEARING_AUDIOLOGY", "VISION_OPTOMETRY",
    "DENTAL_MOBILE_DENTAL", "PODIATRY", "BEHAVIORAL_GERIATRIC_PSYCHIATRY",
    "DEMENTIA_RESPITE_ADULT_DAY",
}

_last_cycle: dict[str, Any] | None = None
logger = logging.getLogger(__name__)


def _load() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("supplier_id", "brand_name", "sector_ids", "branch", "ratings", "involvement", "evidence_refs", "unknown_fields", "freshness", "publication")
    for key in required:
        if key not in record:
            errors.append(f"missing required field: {key}")
    if not record.get("sector_ids"):
        errors.append("sector_ids must not be empty")
    if record.get("involvement") not in VALID_INVOLVEMENT:
        errors.append("invalid involvement")
    status = (record.get("publication") or {}).get("status")
    if status not in VALID_STATUSES:
        errors.append("invalid publication status")
    if status in PUBLIC_STATUSES and (record.get("branch") or {}).get("las_vegas_valley_verified") is not True:
        errors.append("public supplier must have verified Las Vegas Valley service")
    if record.get("involvement") == "OUTCOME_CRITICAL" and not record.get("critical_readiness"):
        errors.append("OUTCOME_CRITICAL supplier requires critical_readiness")
    if not record.get("evidence_refs"):
        errors.append("supplier requires at least one evidence reference")
    return errors


def run_supplier_intelligence_cycle() -> dict[str, Any]:
    """Process the prepared discovery queue without inventing missing evidence.

    The first operational cycle validates and indexes discovered suppliers. Later
    collectors can enrich the same records with regulator and review observations.
    Invalid records stay out of the readable catalog and are returned for repair.
    """
    global _last_cycle
    payload = _load()
    records = payload.get("records", [])
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for record in records:
        errors = _record_errors(record)
        supplier_id = record.get("supplier_id")
        if supplier_id in seen:
            errors.append("duplicate supplier_id")
        if supplier_id:
            seen.add(supplier_id)
        if errors:
            rejected.append({"supplier_id": supplier_id, "errors": errors})
        else:
            accepted.append(record)

    sector_counts = Counter(sector for record in accepted for sector in record["sector_ids"])
    status_counts = Counter(record["publication"]["status"] for record in accepted)
    unresolved = sum(len(record.get("unknown_fields", [])) for record in accepted)
    official_credentials = sum(len(record.get("licenses", [])) for record in accepted)
    records_with_official_credentials = sum(1 for record in accepted if record.get("licenses"))
    records_with_quality_evidence = sum(
        1 for record in accepted if record.get("ratings") or record.get("quality_metrics")
    )
    coverage_gaps = sorted(CANONICAL_SECTORS - set(sector_counts))
    next_queue = [
        "Verify regulated suppliers against Nevada/CMS licensing sources",
        "Resolve branch-specific Google, Yelp and BBB rating observations",
        "Contact outcome-critical suppliers for capacity, price, start date and backup coverage",
    ]
    if coverage_gaps:
        next_queue.append("Expand uncovered canonical sectors")
    _last_cycle = {
        "agent": "supplier-intelligence-agent",
        "market": payload.get("market"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "candidates_read": len(records),
        "records_accepted": len(accepted),
        "records_rejected": len(rejected),
        "public_records": sum(1 for record in accepted if record["publication"]["status"] in PUBLIC_STATUSES),
        "outcome_critical_records": sum(1 for record in accepted if record["involvement"] == "OUTCOME_CRITICAL"),
        "unresolved_fields": unresolved,
        "official_credentials": official_credentials,
        "records_with_official_credentials": records_with_official_credentials,
        "records_with_quality_evidence": records_with_quality_evidence,
        "sector_counts": dict(sorted(sector_counts.items())),
        "coverage_gaps": coverage_gaps,
        "status_counts": dict(sorted(status_counts.items())),
        "rejected": rejected,
        "next_queue": next_queue,
    }
    return deepcopy(_last_cycle)


def supplier_catalog(*, sector: str | None = None, query: str | None = None, include_candidates: bool = False) -> dict[str, Any]:
    payload = _load()
    allowed = VALID_STATUSES if include_candidates else PUBLIC_STATUSES
    normalized_sector = sector.strip().upper() if sector else None
    normalized_query = query.strip().lower() if query else None
    rows: list[dict[str, Any]] = []
    for record in payload.get("records", []):
        if _record_errors(record):
            continue
        if record["publication"]["status"] not in allowed:
            continue
        if normalized_sector and normalized_sector not in record["sector_ids"]:
            continue
        if normalized_query:
            haystack = " ".join([record["brand_name"], *record["sector_ids"], *record.get("services", []), *((record.get("branch") or {}).get("service_area") or [])]).lower()
            if normalized_query not in haystack:
                continue
        rows.append(deepcopy(record))
    rows.sort(key=lambda row: (0 if row["publication"]["status"] == "VERIFIED" else 1, row["brand_name"].lower()))
    return {"market": payload.get("market"), "count": len(rows), "records": rows, "ratings_policy": "SOURCE_SPECIFIC_ONLY", "commercial_influence": "PROHIBITED"}


def supplier_coverage() -> dict[str, Any]:
    cycle = run_supplier_intelligence_cycle()
    return {
        "market": cycle["market"],
        "supplier_count": cycle["records_accepted"],
        "public_supplier_count": cycle["public_records"],
        "sector_count": len(cycle["sector_counts"]),
        "sector_counts": cycle["sector_counts"],
        "coverage_gaps": cycle["coverage_gaps"],
        "status_counts": cycle["status_counts"],
        "unresolved_fields": cycle["unresolved_fields"],
        "official_credentials": cycle["official_credentials"],
        "records_with_official_credentials": cycle["records_with_official_credentials"],
        "records_with_quality_evidence": cycle["records_with_quality_evidence"],
        "last_cycle_at": cycle["started_at"],
    }


def start_supplier_intelligence_scheduler() -> None:
    """Start the prepared-supplier worker immediately and repeat every 24 hours.

    This worker deliberately validates and indexes prepared evidence only. Network
    collectors enrich the candidate file asynchronously; a resident request never
    waits for or triggers live research.
    """
    interval = max(3600, int(os.getenv("OPTIME_SUPPLIER_INTELLIGENCE_INTERVAL_SECONDS", "86400")))

    def _runner() -> None:
        while True:
            try:
                result = run_supplier_intelligence_cycle()
                logger.info(
                    "supplier_intelligence_cycle_completed accepted=%s rejected=%s sectors=%s",
                    result["records_accepted"],
                    result["records_rejected"],
                    len(result["sector_counts"]),
                )
            except Exception:
                logger.exception("supplier_intelligence_cycle_failed")
            time.sleep(interval)

    threading.Thread(target=_runner, name="oomnik-supplier-intelligence", daemon=True).start()
