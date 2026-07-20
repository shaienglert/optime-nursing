import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOP5_PATH = ROOT / "database" / "top5_decision_table.json"
RULES_PATH = ROOT / "database" / "professional_rule_registry.json"
POLICY_PATH = ROOT / "database" / "candidate_governance_policy.json"
OUTPUT_PATH = ROOT / "database" / "recommendation_traceability_matrix.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    top5 = _load_json(TOP5_PATH)
    rules = _load_json(RULES_PATH)
    policy = _load_json(POLICY_PATH)

    rule_inventory = rules.get("rules", [])
    level_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "UNKNOWN": 0}
    for rule in rule_inventory:
        level = str(rule.get("authority_level") or "UNKNOWN").upper()
        if level not in level_counts:
            level = "UNKNOWN"
        level_counts[level] += 1

    entries = []
    for row in top5.get("rows", []):
        trace_lines = row.get("traceability") or []
        unknown_count = int(row.get("unknown_count") or 0)
        verified_count = int(row.get("verified_count") or 0)

        entries.append(
            {
                "recommendation_id": f"REC-{row.get('rank')}",
                "rank": row.get("rank"),
                "facility_id": row.get("facility_id"),
                "facility_name": row.get("facility_name"),
                "decision": {
                    "classification": "OUR_RECOMMENDATION",
                    "status": "ACCEPTED",
                    "hard_rejection_reasons": row.get("hard_rejection_reasons") or [],
                },
                "score": {
                    "total_score": row.get("total_score"),
                    "final_match_score": row.get("final_match_score"),
                    "confidence_score": row.get("confidence_score"),
                },
                "evidence": {
                    "verified_count": verified_count,
                    "unknown_count": unknown_count,
                    "unknown_handling": "UNKNOWN retained and routed to clarify/investigate",
                },
                "explanation": {
                    "rank_reason": row.get("rank_reason"),
                    "traceability_lines": trace_lines,
                },
                "governance": {
                    "policy_reference": "candidate_governance_policy.json",
                    "rule_registry_reference": "professional_rule_registry.json",
                    "authority_inventory": level_counts,
                },
            }
        )

    payload = {
        "phase": 7,
        "generated_at_utc": _utc_now(),
        "source_artifacts": {
            "top5": str(TOP5_PATH.name),
            "rule_registry": str(RULES_PATH.name),
            "candidate_policy": str(POLICY_PATH.name),
        },
        "meta": {
            "scenario_id": top5.get("meta", {}).get("scenario_id"),
            "persona_type": top5.get("meta", {}).get("persona_type"),
            "total_trace_entries": len(entries),
            "governed_rules_count": len(rule_inventory),
            "candidate_lifecycle": policy.get("candidate_lifecycle", []),
        },
        "trace_entries": entries,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"WROTE={OUTPUT_PATH}")
    print(f"TRACE_ENTRIES={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
