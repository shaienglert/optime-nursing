import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "database" / "facility_evidence_matrix_schema.json"
SNAPSHOT_PATH = ROOT / "database" / "facility_evidence_matrix_snapshot.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    schema = _load_json(SCHEMA_PATH)
    snapshot = _load_json(SNAPSHOT_PATH)

    expected_levels = {"SOURCE_OF_TRUTH", "PROVIDER_VERIFIED", "INTELLIGENCE_SIGNAL", "UNVERIFIED"}
    schema_levels = {item.get("level") for item in schema.get("source_hierarchy", [])}
    if schema_levels != expected_levels:
        errors.append("source_hierarchy must contain SOURCE_OF_TRUTH/PROVIDER_VERIFIED/INTELLIGENCE_SIGNAL/UNVERIFIED")

    unknown_policy = schema.get("unknown_handling_policy", {})
    outputs = set(unknown_policy.get("required_output_classes", []))
    if outputs != {"CLARIFY", "INVESTIGATE", "UNKNOWN"}:
        errors.append("unknown handling output classes must be exactly CLARIFY/INVESTIGATE/UNKNOWN")

    scope = snapshot.get("scope", {})
    runtime_count = int(scope.get("runtime_facility_count") or 0)
    canonical_count = int(scope.get("canonical_facility_count") or 0)
    if runtime_count <= 0:
        errors.append("runtime facility count must be > 0")
    if canonical_count < runtime_count:
        errors.append("canonical count cannot be smaller than runtime count")

    status_counts = snapshot.get("verification_status_counts", {})
    status_total = sum(int(v) for v in status_counts.values())
    if status_total != runtime_count:
        errors.append("verification status counts must sum to runtime facility count")

    source_counts = snapshot.get("source_level_counts", {})
    source_total = sum(int(v) for v in source_counts.values())
    if source_total != runtime_count:
        errors.append("source level counts must sum to runtime facility count")

    invalid_levels = sorted(set(source_counts.keys()) - expected_levels)
    if invalid_levels:
        errors.append("invalid source level(s) in snapshot: " + ", ".join(invalid_levels))

    policies = snapshot.get("policies", {})
    if policies.get("unknown_is_not_no") is not True:
        errors.append("unknown_is_not_no policy must be true")

    actions = set(policies.get("insufficient_evidence_actions", []))
    if not {"CLARIFY", "INVESTIGATE", "UNKNOWN"}.issubset(actions):
        errors.append("insufficient evidence actions must include CLARIFY, INVESTIGATE, UNKNOWN")

    county_coverage = scope.get("canonical_county_coverage", {})
    missing_counties = county_coverage.get("counties_missing") or []
    if len(missing_counties) != 3:
        warnings.append("expected three missing counties in canonical coverage")

    unknown_fields = snapshot.get("unknown_field_counts", {})
    if int(unknown_fields.get("confidence_level") or 0) == runtime_count:
        warnings.append("all runtime facilities currently have unknown confidence_level")

    if errors:
        print("EVIDENCE_MATRIX_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("EVIDENCE_MATRIX_VALIDATION=PASS")
    print(f"RUNTIME_FACILITIES={runtime_count}")
    print(f"CANONICAL_FACILITIES={canonical_count}")
    print("UNKNOWN_POLICY=PASS")
    print("SOURCE_HIERARCHY=PASS")
    if warnings:
        print("EVIDENCE_MATRIX_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("EVIDENCE_MATRIX_WARNINGS=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
