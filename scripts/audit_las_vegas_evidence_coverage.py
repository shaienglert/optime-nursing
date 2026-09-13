#!/usr/bin/env python3
"""Audit what the governed Las Vegas universe proves, and what it does not."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def known(value: Any) -> bool:
    return value not in (None, "", "UNKNOWN", [], {})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "LAS_VEGAS_EVIDENCE_COVERAGE.json")
    args = parser.parse_args()

    from sys import path
    path.insert(0, str(REPO_ROOT / "backend"))
    from app.services.canonical_universe import resolve_canonical_universe_path

    payload = json.loads(resolve_canonical_universe_path("las-vegas").read_text(encoding="utf-8"))
    rows = list(payload.get("records") or [])
    fields = {
        "active_or_governed_identity": lambda row: str(row.get("license_status") or "").upper() in {"ACTIVE", "ACTIVE_BUSINESS_LICENSE_IDENTITY", "UNREGULATED_SENIOR_HOUSING_PROVIDER_VERIFIED"},
        "license_expiration": lambda row: known(row.get("expiration_date")),
        "regulatory_detail_url": lambda row: known(row.get("detail_url")),
        "licensed_or_certified_capacity": lambda row: known(row.get("licensed_capacity")) or known(row.get("certified_beds")),
        "phone": lambda row: known(row.get("phone")),
        "cms_quality_profile": lambda row: all(known(row.get(key)) for key in ("cms_overall_rating", "cms_health_inspection_rating", "cms_staffing_rating", "cms_quality_measure_rating")),
        "official_provider_website": lambda row: known(row.get("official_website")),
        "provider_housing_evidence": lambda row: known(row.get("provider_housing_evidence")),
        "independent_living_primary_evidence": lambda row: known(row.get("independent_living_primary_evidence")),
        "memory_care_confirmed": lambda row: row.get("memory_care_classification") == "CONFIRMED",
    }
    totals = {name: sum(bool(check(row)) for row in rows) for name, check in fields.items()}
    by_type: dict[str, dict[str, int]] = defaultdict(dict)
    for facility_type in sorted({str(row.get("canonical_type") or "UNKNOWN") for row in rows}):
        subset = [row for row in rows if str(row.get("canonical_type") or "UNKNOWN") == facility_type]
        by_type[facility_type] = {"facilities": len(subset), **{name: sum(bool(check(row)) for row in subset) for name, check in fields.items()}}

    report = {
        "scope": "Las Vegas Valley, Nevada only",
        "source": "checksum-validated Las Vegas runtime projection plus verified housing overlays",
        "facilities": len(rows),
        "facility_types": dict(Counter(str(row.get("canonical_type") or "UNKNOWN") for row in rows)),
        "evidence_coverage": totals,
        "evidence_coverage_by_type": by_type,
        "recommendation_policy": "Missing material service evidence remains UNKNOWN and blocks final recommendation; it never becomes a positive inference.",
        "research_priority": [
            "Resolve current-license status for any record lacking active/governed identity.",
            "Obtain official-provider evidence for medication, ADL, memory care, rehabilitation, pricing, availability and Medicaid only when relevant to a client MUST.",
            "Use regulatory and CMS quality facts as governed tie-break evidence, not paid-placement signals.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
