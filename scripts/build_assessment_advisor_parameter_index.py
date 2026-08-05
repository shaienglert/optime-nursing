from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "database" / "optime_parameter_registry.json"
ACQUISITION_AUDIT_PATH = ROOT / "frontend" / "src" / "data" / "parameter-acquisition-audit.json"
OUTPUT_PATH = ROOT / "frontend" / "src" / "data" / "assessment-advisor-parameter-intelligence.json"

FIELDS = (
    "parameter_id",
    "family",
    "display_name",
    "consumer_description",
    "ranking_eligibility",
    "hard_filter_eligibility",
    "requires_facility_confirmation",
    "dynamic",
    "personalization_tags",
    "freshness_rule",
)


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    acquisition_audit = json.loads(ACQUISITION_AUDIT_PATH.read_text(encoding="utf-8"))
    acquisition_by_id = {record["Parameter ID"]: record for record in acquisition_audit.get("records") or []}
    records = registry.get("records") or []
    compact_records: list[dict[str, Any]] = []

    for record in records:
        compact = {field: record.get(field) for field in FIELDS}
        acquisition = acquisition_by_id.get(record.get("parameter_id"), {})
        compact.update(
            {
                "criticality": acquisition.get("Criticality", "STANDARD"),
                "source_authority": acquisition.get("Source authority", "UNKNOWN"),
                "current_coverage_percent": acquisition.get("Current coverage percent", 0),
                "recommended_action_when_missing": acquisition.get("Recommended ACTION when missing", "Keep UNKNOWN and verify."),
            }
        )
        compact_records.append(compact)

    payload = {
        "sources": ["database/optime_parameter_registry.json", "frontend/src/data/parameter-acquisition-audit.json"],
        "source_generated_at_utc": registry.get("generated_at_utc"),
        "record_count": len(compact_records),
        "records": compact_records,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if len(compact_records) != registry.get("record_count"):
        raise ValueError("Advisor parameter index count does not match the canonical registry")

    print(f"WROTE {OUTPUT_PATH} ({len(compact_records)} parameters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())