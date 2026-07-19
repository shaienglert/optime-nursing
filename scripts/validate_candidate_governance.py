import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "database" / "candidate_governance_policy.json"
ENGINE_PATH = ROOT / "frontend" / "src" / "lib" / "optime-v2-engine.ts"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    policy = _load_json(POLICY_PATH)
    engine_text = ENGINE_PATH.read_text(encoding="utf-8")

    expected_lifecycle = ["GENERATED", "EVALUATED", "ACCEPTED_OR_REJECTED", "RANKED", "DISPLAYED"]
    if policy.get("candidate_lifecycle") != expected_lifecycle:
        errors.append("candidate_lifecycle sequence mismatch")

    required_contract_keys = policy.get("output_contract", {}).get("required_engine_keys", [])
    for key in required_contract_keys:
        if not re.search(rf"\b{re.escape(key)}\b", engine_text):
            errors.append(f"engine key not found in source: {key}")

    required_summary_keys = policy.get("output_contract", {}).get("required_rejection_summary_keys", [])
    for key in required_summary_keys:
        if not re.search(rf"\b{re.escape(key)}\b", engine_text):
            errors.append(f"rejection summary key not found in source: {key}")

    checks = {
        "accepted_filter": r"accepted\s*=\s*recommendations\s*\.\s*filter\(\(recommendation\)\s*=>\s*recommendation\.hardRejectionReasons\.length\s*===\s*0",
        "fallback_behavior": r"displayedRecommendations\s*=\s*accepted\.length\s*>\s*0\s*\?\s*accepted\s*:\s*fallbackRecommendations",
        "unknown_not_no": r"UNKNOWN items reduce confidence only and are never treated as NO",
        "fit_first_tie_break": r"Completeness acts only as tie-breaker when fit is equivalent",
    }

    for check_name, pattern in checks.items():
        if not re.search(pattern, engine_text):
            errors.append(f"missing governed pattern: {check_name}")

    taxonomy = set(policy.get("hard_rejection_taxonomy", []))
    expected_taxonomy = {
        "BUDGET",
        "CARE_LEVEL",
        "ACTIVITY_OR_LIFESTYLE",
        "FUTURE_CARE_PATH",
        "DISTANCE",
        "VERIFICATION",
        "UNKNOWN",
    }
    if taxonomy != expected_taxonomy:
        errors.append("hard_rejection_taxonomy mismatch")

    if "rejectedByUnknown" not in engine_text:
        warnings.append("rejectedByUnknown marker not found")

    if errors:
        print("CANDIDATE_GOVERNANCE_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("CANDIDATE_GOVERNANCE_VALIDATION=PASS")
    print("CANDIDATE_LIFECYCLE=PASS")
    print("ACCEPTED_REJECTED_BOUNDARY=PASS")
    print("UNKNOWN_POLICY=PASS")
    print("FALLBACK_BEHAVIOR=PASS")
    if warnings:
        print("CANDIDATE_GOVERNANCE_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("CANDIDATE_GOVERNANCE_WARNINGS=NO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
