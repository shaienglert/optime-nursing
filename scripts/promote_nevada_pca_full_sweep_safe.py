from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests

try:
    from scripts.enrich_nevada_pca_operational_primary_sources import fetch, norm, strip_html
except ModuleNotFoundError:
    from enrich_nevada_pca_operational_primary_sources import fetch, norm, strip_html

UNKNOWN = "UNKNOWN"

POSITIVE_ONLY_FIELDS = (
    "bathing_assistance",
    "dressing_assistance",
    "transfer_assistance",
    "medication_reminders",
    "meal_preparation",
    "light_housekeeping",
    "liability_insurance_verified",
    "workers_comp_verified",
    "background_check_verified",
    "fixed_caregiver_possible",
)
KNOWN_SCALAR_FIELDS = (
    "minimum_billable_hours",
    "minimum_visit_minutes",
    "employment_model",
    "availability_status",
)


def _known(value: Any) -> bool:
    return value not in (None, "", UNKNOWN, [], {})


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _strong_identity_basis(row: dict[str, Any]) -> str | None:
    urls = []
    primary = str(row.get("primary_source_url") or "").strip()
    if primary.startswith("http"):
        urls.append(primary)
    for value in row.get("source_pages") or []:
        text = str(value or "").strip()
        if text.startswith("http") and text not in urls:
            urls.append(text)
    if not urls:
        return None

    texts: list[str] = []
    for url in urls[:7]:
        try:
            body, status, _ = fetch(url)
        except requests.RequestException:
            continue
        if status == 200:
            texts.append(strip_html(body))
    if not texts:
        return None
    combined = " ".join(texts)
    normalized = norm(combined)
    digits = _digits(combined)

    phone = _digits(row.get("phone"))
    if len(phone) >= 7 and phone[-7:] in digits:
        return "PRIMARY_SOURCE_EXACT_PHONE"

    address = norm(row.get("address"))
    city = norm(row.get("city"))
    parts = address.split()
    street_number = parts[0] if parts and parts[0].isdigit() else ""
    street_tokens = [p for p in parts[1:] if len(p) >= 4][:3]
    if street_number and street_number in normalized and city and city in normalized and sum(t in normalized for t in street_tokens) >= 1:
        return "PRIMARY_SOURCE_STRONG_ADDRESS_CITY"

    license_number = str(row.get("license_number") or "")
    license_root = _digits(license_number.split("-")[0])
    if license_root and re.search(rf"\b{re.escape(license_root)}\s*(?:pcs|personal care)", normalized):
        return "PRIMARY_SOURCE_EXACT_LICENSE_ROOT"

    return None


def _safe_row(row: dict[str, Any], identity_basis: str) -> dict[str, Any]:
    promoted = {
        "agency_id": row.get("agency_id") or UNKNOWN,
        "agency_name": row.get("agency_name") or UNKNOWN,
        "license_number": row.get("license_number") or UNKNOWN,
        "license_status": row.get("license_status") or "ACTIVE",
        "address": row.get("address") or UNKNOWN,
        "city": row.get("city") or UNKNOWN,
        "state": row.get("state") or "NV",
        "zip": row.get("zip") or UNKNOWN,
        "phone": row.get("phone") or UNKNOWN,
        "primary_source_url": row.get("primary_source_url") or UNKNOWN,
        "source_pages": row.get("source_pages") or [],
        "identity_verified": True,
        "identity_basis": identity_basis,
        "serves_las_vegas_valley": True,
        "hourly_rate": UNKNOWN,
        "hourly_rate_for_requested_schedule": UNKNOWN,
        "languages": row.get("languages") if isinstance(row.get("languages"), list) else [],
        "published_hourly_rate_candidates": row.get("published_hourly_rate_candidates") if isinstance(row.get("published_hourly_rate_candidates"), list) else [],
        "evidence_summary": "Automatically staged from the complete PCA primary-source sweep after re-verifying strong identity by exact phone, strong address+city, or license root. Negative/absent website signals are never promoted as NO; they remain UNKNOWN.",
    }
    for field in POSITIVE_ONLY_FIELDS:
        promoted[field] = True if row.get(field) is True else UNKNOWN
    for field in KNOWN_SCALAR_FIELDS:
        promoted[field] = row.get(field) if _known(row.get(field)) else UNKNOWN
    return promoted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="reports/NEVADA_PCA_OPERATIONAL_FULL_SWEEP.json")
    ap.add_argument("--existing", default="data/nevada/verified/pca_operational_live_promotions.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_SAFE_AUTO_PROMOTIONS.json")
    args = ap.parse_args()

    sweep = json.loads(Path(args.sweep).read_text(encoding="utf-8"))
    existing_path = Path(args.existing)
    existing = json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.is_file() else {"records": []}
    existing_licenses = {
        str(row.get("license_number") or "").strip()
        for row in existing.get("records") or []
        if str(row.get("license_number") or "").strip()
    }

    records = []
    rejected_weak_identity = []
    for row in sweep.get("records") or []:
        license_number = str(row.get("license_number") or "").strip()
        if row.get("identity_verified") is not True or not license_number or license_number in existing_licenses:
            continue
        basis = _strong_identity_basis(row)
        if not basis:
            rejected_weak_identity.append(license_number)
            continue
        records.append(_safe_row(row, basis))

    payload = {
        "schema_version": "nevada-pca-safe-auto-promotions-v1.1.0",
        "source": "NEVADA_PCA_OPERATIONAL_FULL_SWEEP",
        "candidate_count": len(records),
        "rejected_weak_identity_count": len(rejected_weak_identity),
        "rejected_weak_identity_licenses": sorted(rejected_weak_identity),
        "policy": {
            "identity": "Auto-promotion requires a second strong identity check against the primary source: exact phone, strong address+city, or license root. Name+city alone is never sufficient.",
            "negative_signal": "Website absence never becomes a negative fact; False/absent service and compliance fields remain UNKNOWN.",
            "pricing": "Published hourly examples remain contextual candidates and never become the requested-schedule hourly rate automatically.",
            "production": "These records remain staging until merged through the live HCQC/ALiS allowlist gate.",
        },
        "records": sorted(records, key=lambda r: (str(r.get("city") or ""), str(r.get("agency_name") or ""), str(r.get("license_number") or ""))),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "safe_auto_promotion_candidates": len(records),
        "rejected_weak_identity": len(rejected_weak_identity),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
