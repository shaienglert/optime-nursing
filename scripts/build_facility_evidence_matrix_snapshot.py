import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "optime_nursing.db"
CANONICAL_PATH = ROOT / "database" / "florida_senior_living_inventory.json"
OUTPUT_PATH = ROOT / "database" / "facility_evidence_matrix_snapshot.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Runtime DB not found: {DB_PATH}")

    canonical = _load_json(CANONICAL_PATH)
    canonical_record_count = int(canonical.get("record_count") or 0)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    facilities = cur.execute(
        """
        select f.id, f.name, f.state, f.city,
               f.cms_id,
               f.overall_rating, f.quality_rating, f.staffing_rating, f.inspection_rating,
               f.confidence_level,
               f.overall_optime_score,
               p.sources_used as intelligence_sources_used,
               p.regulatory_risk_index,
               p.litigation_risk_index,
               p.social_energy_index,
               p.community_engagement_index,
               p.reputation_index,
               coalesce(vm.capability_count, 0) as verification_capability_count,
               coalesce(vm.conflict_count, 0) as verification_conflict_count
        from facilities f
        left join facility_intelligence_profiles p on p.facility_id = f.id
        left join (
          select
            facility_id,
            count(*) as capability_count,
            sum(case when coalesce(conflict_count, 0) > 0 then 1 else 0 end) as conflict_count
          from facility_verification_memory
          group by facility_id
        ) vm on vm.facility_id = f.id
        where f.state = 'FL'
        """
    ).fetchall()

    canonical_counties = Counter()
    for row in canonical.get("records", []):
        county = str(row.get("county") or "UNKNOWN").strip() or "UNKNOWN"
        canonical_counties[county] += 1

    status_counts = Counter()
    source_level_counts = Counter()
    unknown_field_counts = Counter()

    for row in facilities:
        capability_count = int(row["verification_capability_count"] or 0)
        conflict_count = int(row["verification_conflict_count"] or 0)
        if conflict_count > 0:
            status = "CONFLICTED"
        elif capability_count >= 3:
            status = "VERIFIED"
        elif capability_count > 0:
            status = "PARTIALLY_VERIFIED"
        else:
            status = "UNKNOWN"
        status_counts[status] += 1

        has_cms = bool(row["cms_id"])
        has_provider_verification = capability_count > 0
        has_signal_data = any(
            row[key] is not None
            for key in [
                "social_energy_index",
                "community_engagement_index",
                "reputation_index",
                "regulatory_risk_index",
                "litigation_risk_index",
            ]
        )

        if has_cms:
            source_level_counts["SOURCE_OF_TRUTH"] += 1
        elif has_provider_verification:
            source_level_counts["PROVIDER_VERIFIED"] += 1
        elif has_signal_data:
            source_level_counts["INTELLIGENCE_SIGNAL"] += 1
        else:
            source_level_counts["UNVERIFIED"] += 1

        if row["overall_rating"] is None and row["quality_rating"] is None and row["staffing_rating"] is None and row["inspection_rating"] is None:
            unknown_field_counts["quality_and_cms_ratings"] += 1
        if row["confidence_level"] is None:
            unknown_field_counts["confidence_level"] += 1
        if row["overall_optime_score"] is None:
            unknown_field_counts["overall_optime_score"] += 1

    snapshot = {
        "generated_at_utc": _utc_now(),
        "phase": 4,
        "scope": {
            "runtime_state": "FL",
            "runtime_facility_count": len(facilities),
            "canonical_facility_count": canonical_record_count,
            "canonical_county_coverage": {
                "counties_total": int(canonical.get("counties_total") or 0),
                "counties_covered": int(canonical.get("counties_covered") or 0),
                "counties_missing": canonical.get("counties_missing") or [],
            },
        },
        "verification_status_counts": dict(status_counts),
        "source_level_counts": dict(source_level_counts),
        "unknown_field_counts": dict(unknown_field_counts),
        "county_distribution_from_canonical": dict(canonical_counties),
        "policies": {
            "unknown_is_not_no": True,
            "conflict_requires_review": True,
            "insufficient_evidence_actions": ["CLARIFY", "INVESTIGATE", "UNKNOWN"],
        },
    }

    OUTPUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"WROTE={OUTPUT_PATH}")
    print(f"RUNTIME_FACILITIES={len(facilities)}")
    print(f"CANONICAL_FACILITIES={canonical_record_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
