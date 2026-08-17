from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "database" / "nevada_facility_universe_canonical.json"
OUT_DIR = ROOT / "reports" / "guardian"
OUT = OUT_DIR / "nevada_facility_universe_audit.json"


def present(value):
    return value not in (None, "", [], {}, "UNKNOWN", "unknown")


def main() -> int:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload.get("records") or []
    if not isinstance(records, list):
        raise SystemExit("Nevada canonical universe has no records[] array")

    type_counts = Counter()
    canonical_type_counts = Counter()
    city_counts = Counter()
    county_counts = Counter()
    license_status_counts = Counter()
    evidence_source_counts = Counter()
    las_vegas_valley = 0
    with_license = with_cms = with_npi = with_licensed_capacity = with_certified_beds = 0
    with_phone = with_website = with_source_evidence = 0

    for record in records:
        facility_type = record.get("facility_type") or record.get("primary_community_type") or "UNKNOWN"
        type_counts[str(facility_type)] += 1
        canonical_type_counts[str(record.get("canonical_type") or "UNKNOWN")] += 1
        city_counts[str(record.get("city") or "UNKNOWN")] += 1
        county_counts[str(record.get("county") or "UNKNOWN")] += 1
        license_status_counts[str(record.get("license_status") or "UNKNOWN")] += 1
        las_vegas_valley += int(record.get("is_las_vegas_valley") is True)
        with_license += int(present(record.get("nevada_license_id")))
        with_cms += int(present(record.get("cms_certification_number") or record.get("cms_ccn") or record.get("ccn")))
        with_npi += int(present(record.get("npi")))
        with_licensed_capacity += int(present(record.get("licensed_beds_capacity")))
        with_certified_beds += int(present(record.get("certified_beds")))
        with_phone += int(present(record.get("phone")))
        with_website += int(present(record.get("website")))
        evidence = record.get("source_evidence") or {}
        with_source_evidence += int(bool(evidence))
        items = evidence.values() if isinstance(evidence, dict) else evidence if isinstance(evidence, list) else []
        for item in items:
            if isinstance(item, dict) and item.get("source_name"):
                evidence_source_counts[str(item["source_name"])] += 1

    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "declared_record_count": payload.get("record_count"),
        "computed_record_count": len(records),
        "record_count_matches": payload.get("record_count") in (None, len(records)),
        "las_vegas_valley_count": las_vegas_valley,
        "outside_las_vegas_valley_count": len(records) - las_vegas_valley,
        "facility_type_counts": dict(type_counts.most_common()),
        "canonical_type_counts": dict(canonical_type_counts.most_common()),
        "county_counts": dict(county_counts.most_common()),
        "top_cities": dict(city_counts.most_common(25)),
        "license_status_counts": dict(license_status_counts.most_common()),
        "identity_and_evidence_coverage": {
            "with_nevada_license_id": with_license,
            "with_cms_ccn": with_cms,
            "with_npi": with_npi,
            "with_licensed_capacity": with_licensed_capacity,
            "with_certified_beds": with_certified_beds,
            "with_phone": with_phone,
            "with_website": with_website,
            "with_source_evidence": with_source_evidence
        },
        "evidence_source_occurrences": dict(evidence_source_counts.most_common()),
        "semantic_guardrails": [
            "Coverage is not recommendation influence.",
            "Missing information is UNKNOWN, not negative evidence.",
            "Facility type is not a blanket eligibility gate.",
            "CMS evidence applies only where the facility/source identity is verified."
        ]
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
