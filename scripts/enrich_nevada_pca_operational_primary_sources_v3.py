from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from enrich_nevada_pca_operational_primary_sources import UNKNOWN, fetch, same_domain_links, strip_html
from enrich_nevada_pca_operational_primary_sources_v2 import discover_candidates, identity_matches


def _contains(text: str, *terms: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _minimum_weekly_hours(text: str) -> int | str:
    lower = text.lower()
    patterns = (
        r"(?:minimum|min\.?)[^\d]{0,25}(\d{1,3})\s*(?:hour|hr)s?\s*(?:per|a)\s*week",
        r"(\d{1,3})\s*(?:hour|hr)s?\s*(?:per|a)\s*week[^.]{0,30}(?:minimum|min\.)",
        r"weekly\s+(?:minimum|min\.)[^\d]{0,20}(\d{1,3})\s*(?:hour|hr)s?",
    )
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.I)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 168:
                return value
    return UNKNOWN


def _placement_speed(text: str) -> str:
    lower = text.lower()
    if re.search(r"(?:care|services?|caregiver)[^.]{0,80}(?:within|in)\s*24\s*hours?", lower):
        return "CARE_CAN_START_WITHIN_24_HOURS"
    if re.search(r"(?:care|services?|caregiver)[^.]{0,80}(?:within|in)\s*48\s*hours?", lower):
        return "CARE_CAN_START_WITHIN_48_HOURS"
    return UNKNOWN


def extract_extended_positive_facts(text: str) -> dict[str, Any]:
    lower = text.lower()
    return {
        "post_surgical_care": True if _contains(lower, "post-surgical", "post surgical", "post surgery", "after surgery", "hospital-to-home", "hospital to home", "transitional care") else UNKNOWN,
        "in_facility_care_available": True if _contains(lower, "care in assisted living", "assisted living facility", "care in a facility", "facility staffing", "in-facility care") else UNKNOWN,
        "backup_caregiver_available": True if _contains(lower, "backup caregiver", "backup coverage", "replacement caregiver", "caregiver replacement") else UNKNOWN,
        "registered_nurse_oversight": True if _contains(lower, "registered nurse oversight", "rn oversight", "nurse supervised", "rn supervised", "nurse-led care") else UNKNOWN,
        "bonded_verified": True if _contains(lower, "bonded and insured", "insured and bonded", "licensed, bonded") else UNKNOWN,
        "overnight_care_available": True if _contains(lower, "overnight care", "overnight caregiver", "overnight support") else UNKNOWN,
        "live_in_care_available": True if _contains(lower, "live-in care", "live in care", "live-in caregiver") else UNKNOWN,
        "long_term_care_insurance_verified": True if _contains(lower, "long-term care insurance", "long term care insurance", "ltc insurance") else UNKNOWN,
        "va_benefit_support_verified": True if _contains(lower, "va benefits", "veterans benefits", "aid and attendance", "va community care") else UNKNOWN,
        "medicaid_service_verified": True if re.search(r"\bmedicaid\b", lower) else UNKNOWN,
        "private_pay_verified": True if _contains(lower, "private pay", "private-pay", "self pay", "self-pay") else UNKNOWN,
        "minimum_weekly_hours": _minimum_weekly_hours(text),
        "typical_placement_speed": _placement_speed(text),
    }


def verify_candidate_v3(candidate: dict[str, str], task: dict[str, Any], throttle: float) -> dict[str, Any] | None:
    url = candidate["url"]
    try:
        body, status, final_url = fetch(url)
    except requests.RequestException:
        return None
    if status != 200:
        return None

    page_texts = [strip_html(body)]
    pages = [final_url]
    identity = identity_matches(page_texts[0], task)
    for link in same_domain_links(final_url, body):
        if throttle:
            time.sleep(throttle)
        try:
            child_body, child_status, child_final = fetch(link)
        except requests.RequestException:
            continue
        if child_status != 200:
            continue
        child_text = strip_html(child_body)
        page_texts.append(child_text)
        pages.append(child_final)
        if not identity and identity_matches(child_text, task):
            identity = True
    if not identity:
        return None

    # Reuse the governed V2 extraction, then add only explicit positive extended facts.
    from enrich_nevada_pca_operational_primary_sources import extract_operational_facts
    combined = " ".join(page_texts)
    facts = extract_operational_facts(combined)
    facts.update(extract_extended_positive_facts(combined))
    return {
        "primary_source_url": final_url,
        "discovery_method": candidate["discovery_method"],
        "source_pages": pages,
        "identity_verified": True,
        "serves_las_vegas_valley": True if any(token in combined.lower() for token in ("las vegas", "north las vegas", "henderson", "clark county")) else UNKNOWN,
        **facts,
    }


def research_task_v3(task: dict[str, Any], throttle: float) -> dict[str, Any]:
    base = {
        "agency_id": task.get("agency_id") or UNKNOWN,
        "agency_name": task.get("agency_name") or UNKNOWN,
        "license_number": task.get("license_number") or UNKNOWN,
        "license_status": task.get("license_status") or UNKNOWN,
        "address": task.get("address") or UNKNOWN,
        "city": task.get("city") or UNKNOWN,
        "state": task.get("state") or "NV",
        "zip": task.get("zip") or UNKNOWN,
        "phone": task.get("phone") or UNKNOWN,
        "hcqc_detail_url": task.get("hcqc_detail_url") or UNKNOWN,
        "identity_verified": False,
        "primary_source_url": UNKNOWN,
        "serves_las_vegas_valley": UNKNOWN,
        "source_pages": [],
    }
    candidates = discover_candidates(task)
    base["candidate_count"] = len(candidates)
    base["candidate_discovery_methods"] = sorted({row["discovery_method"] for row in candidates})
    for candidate in candidates:
        verified = verify_candidate_v3(candidate, task, throttle)
        if verified:
            base.update(verified)
            base["research_status"] = "PRIMARY_SOURCE_VERIFIED"
            base["policy"] = "Primary source identity is verified before extraction. Extended fields are positive-only; absent facts remain UNKNOWN."
            return base
    base["research_status"] = "SOURCE_NOT_FOUND" if not candidates else "CANDIDATES_NOT_IDENTITY_VERIFIED"
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH_V3.json")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--throttle", type=float, default=0.05)
    args = ap.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    tasks = list(queue.get("tasks") or [])
    start = max(0, args.offset)
    selected = tasks[start:start + max(0, args.limit)]
    records = [research_task_v3(task, max(0.0, args.throttle)) for task in selected]
    payload = {
        "schema_version": "nevada-pca-operational-primary-research-v3.0.0",
        "queue_task_count": len(tasks),
        "attempted": len(selected),
        "identity_verified": sum(1 for row in records if row.get("identity_verified") is True),
        "source_not_found": sum(1 for row in records if row.get("research_status") == "SOURCE_NOT_FOUND"),
        "candidates_not_identity_verified": sum(1 for row in records if row.get("research_status") == "CANDIDATES_NOT_IDENTITY_VERIFIED"),
        "records": records,
        "policy": "Staging evidence only. Extended operational facts are explicit-positive only; missing facts remain UNKNOWN.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("attempted", "identity_verified", "source_not_found", "candidates_not_identity_verified")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
