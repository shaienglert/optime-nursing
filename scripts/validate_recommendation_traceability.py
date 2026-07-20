import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TRACE_PATH = ROOT / "database" / "recommendation_traceability_matrix.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    payload = _load_json(TRACE_PATH)
    trace_entries = payload.get("trace_entries", [])
    meta = payload.get("meta", {})

    if int(payload.get("phase") or 0) != 7:
        errors.append("traceability matrix phase must be 7")

    if len(trace_entries) != 5:
        errors.append("traceability matrix must contain 5 entries for top-5")

    if int(meta.get("total_trace_entries") or 0) != len(trace_entries):
        errors.append("meta total_trace_entries must equal trace entry count")

    lifecycle = meta.get("candidate_lifecycle") or []
    expected_lifecycle = ["GENERATED", "EVALUATED", "ACCEPTED_OR_REJECTED", "RANKED", "DISPLAYED"]
    if lifecycle != expected_lifecycle:
        errors.append("candidate lifecycle mismatch in traceability meta")

    unknown_positive_count = 0

    for index, entry in enumerate(trace_entries, start=1):
        rec_id = str(entry.get("recommendation_id") or "")
        if not rec_id:
            errors.append(f"entry {index} missing recommendation_id")

        decision = entry.get("decision") or {}
        if decision.get("classification") != "OUR_RECOMMENDATION":
            errors.append(f"entry {index} classification must be OUR_RECOMMENDATION")
        if decision.get("status") != "ACCEPTED":
            errors.append(f"entry {index} status must be ACCEPTED")

        hard_rejections = decision.get("hard_rejection_reasons") or []
        if len(hard_rejections) != 0:
            errors.append(f"entry {index} has hard rejection reasons but is marked accepted")

        explanation = entry.get("explanation") or {}
        if not str(explanation.get("rank_reason") or "").strip():
            errors.append(f"entry {index} missing rank_reason")

        traceability_lines = explanation.get("traceability_lines") or []
        if not isinstance(traceability_lines, list) or len(traceability_lines) == 0:
            errors.append(f"entry {index} missing traceability lines")

        evidence = entry.get("evidence") or {}
        unknown_count = int(evidence.get("unknown_count") or 0)
        if unknown_count > 0:
            unknown_positive_count += 1

        if "unknown_handling" not in evidence:
            errors.append(f"entry {index} missing unknown handling statement")

        score = entry.get("score") or {}
        if float(score.get("total_score") or 0) <= 0:
            errors.append(f"entry {index} total_score must be > 0")

        governance = entry.get("governance") or {}
        inv = governance.get("authority_inventory") or {}
        total_rules = sum(int(inv.get(level) or 0) for level in ["A", "B", "C", "D", "UNKNOWN"])
        if total_rules <= 0:
            errors.append(f"entry {index} invalid authority inventory totals")

    if unknown_positive_count == 0:
        warnings.append("no unknown evidence surfaced in trace entries")

    if errors:
        print("TRACEABILITY_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("TRACEABILITY_VALIDATION=PASS")
    print(f"TRACE_ENTRIES={len(trace_entries)}")
    print(f"UNKNOWN_POSITIVE_ENTRIES={unknown_positive_count}")
    if warnings:
        print("TRACEABILITY_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("TRACEABILITY_WARNINGS=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
