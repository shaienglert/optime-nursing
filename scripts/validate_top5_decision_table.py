import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOP5_PATH = ROOT / "database" / "top5_decision_table.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    payload = _load_json(TOP5_PATH)
    rows = payload.get("rows", [])
    meta = payload.get("meta", {})

    if int(payload.get("phase") or 0) != 6:
        errors.append("top5 payload phase must be 6")

    if len(rows) != 5:
        errors.append("top5 table must contain exactly 5 rows")

    expected_ranks = [1, 2, 3, 4, 5]
    row_ranks = [int(row.get("rank") or 0) for row in rows]
    if row_ranks != expected_ranks:
        errors.append("row ranks must be exactly 1..5 in order")

    required_fields = [
        "facility_id",
        "facility_name",
        "total_score",
        "final_match_score",
        "confidence_score",
        "verified_count",
        "unknown_count",
        "hard_rejection_reasons",
        "rank_reason",
        "traceability",
    ]

    for i, row in enumerate(rows, start=1):
        for field in required_fields:
            if field not in row:
                errors.append(f"row {i} missing field: {field}")

        if row.get("hard_rejection_reasons"):
            errors.append(f"row {i} has hard rejection reasons but appears in top5 accepted list")

        if float(row.get("total_score") or 0) <= 0:
            errors.append(f"row {i} total_score must be > 0")

        if not str(row.get("rank_reason") or "").strip():
            errors.append(f"row {i} rank_reason must be non-empty")

        traceability = row.get("traceability") or []
        if not isinstance(traceability, list) or len(traceability) == 0:
            errors.append(f"row {i} traceability must be a non-empty list")

    if int(meta.get("accepted_count") or 0) < 5:
        errors.append("meta.accepted_count must be >= 5")

    persona_type = str(meta.get("persona_type") or "").strip()
    if not persona_type:
        warnings.append("persona_type is empty")

    unknown_total = sum(int(row.get("unknown_count") or 0) for row in rows)
    if unknown_total == 0:
        warnings.append("no unknown requirements in top5; verify scenario realism")

    if errors:
        print("TOP5_DECISION_TABLE_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("TOP5_DECISION_TABLE_VALIDATION=PASS")
    print(f"TOP5_ROWS={len(rows)}")
    print(f"PERSONA_TYPE={persona_type}")
    print(f"UNKNOWN_TOTAL={unknown_total}")
    if warnings:
        print("TOP5_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("TOP5_WARNINGS=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
