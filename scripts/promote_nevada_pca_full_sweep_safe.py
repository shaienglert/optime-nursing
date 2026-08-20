from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


def _safe_row(row: dict[str, Any]) -> dict[str, Any]:
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
        "identity_basis": "FULL_SWEEP_PRIMARY_SOURCE_STRONG_IDENTITY",
        "serves_las_vegas_valley": True,
        "hourly_rate": UNKNOWN,
        "hourly_rate_for_requested_schedule": UNKNOWN,
        "languages": row.get("languages") if isinstance(row.get("languages"), list) else [],
        "published_hourly_rate_candidates": row.get("published_hourly_rate_candidates") if isinstance(row.get("published_hourly_rate_candidates"), list) else [],
        "evidence_summary": "Automatically staged from a complete primary-source sweep after strong licensed-agency identity verification. Negative/absent website signals are never promoted as NO; they remain UNKNOWN.",
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
    for row in sweep.get("records") or []:
        license_number = str(row.get("license_number") or "").strip()
        if row.get("identity_verified") is not True or not license_number or license_number in existing_licenses:
            continue
        records.append(_safe_row(row))

    payload = {
        "schema_version": "nevada-pca-safe-auto-promotions-v1.0.0",
        "source": "NEVADA_PCA_OPERATIONAL_FULL_SWEEP",
        "candidate_count": len(records),
        "policy": {
            "identity": "Only full-sweep rows already verified against the licensed agency identity are eligible.",
            "negative_signal": "Website absence never becomes a negative fact; False/absent service and compliance fields remain UNKNOWN.",
            "pricing": "Published hourly examples remain contextual candidates and never become the requested-schedule hourly rate automatically.",
            "production": "These records remain staging until merged through the live HCQC/ALiS allowlist gate.",
        },
        "records": sorted(records, key=lambda r: (str(r.get("city") or ""), str(r.get("agency_name") or ""), str(r.get("license_number") or ""))),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"safe_auto_promotion_candidates": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
