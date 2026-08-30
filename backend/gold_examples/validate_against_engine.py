"""Run the real MUST-gate engine (client_intent_runtime.evaluate_candidate_intent)
against every gold example that carries a `synthetic_facility_row`, and report
whether the engine's actual verdict matches the gold `must_gates` expectation.

This intentionally does not hit any database or live registry: `synthetic_facility_row`
is a fixed, reviewed snapshot of exactly the evidence each case is about, so the
result only changes when the *logic* changes -- not when live data drifts. Cases
without a `synthetic_facility_row` (frontend/pipeline-level cases, and disputed
policy questions) are reported as SKIPPED, not failed.

Usage:
    cd backend && python gold_examples/validate_against_engine.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent

DATASET = Path(__file__).with_name("nursing_gold_v1.jsonl")


def load_cases() -> list[dict]:
    cases = []
    with DATASET.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def gate_status(result: dict, key: str) -> str:
    if key in result["must_pass"]:
        return "PASS"
    if key in result["must_fail"]:
        return "FAIL"
    return "PENDING_VERIFICATION"


def run_case(case: dict) -> tuple[bool, list[str]]:
    row = dict(case["synthetic_facility_row"])
    resident = case["resident"]

    strategy = {
        "signals": {
            "adl_support_needed": any(g["key"] == "ADL_SUPPORT_AVAILABLE" for g in case["must_gates"]),
            "medication_support_needed": any(g["key"] == "MEDICATION_SUPPORT_AVAILABLE" for g in case["must_gates"]),
        },
        "household": {},
    }
    human_context = {"signals": {}}
    intent = build_client_intent(
        {"locationCity": resident.get("location_city") or ""},
        resident.get("natural_language_query") or "",
        strategy,
        human_context,
    )
    result = evaluate_candidate_intent(row, intent)

    notes = []
    ok = True
    for gate in case["must_gates"]:
        actual = gate_status(result, gate["key"])
        expected = gate["status"]
        if actual != expected:
            ok = False
            notes.append(f"{gate['key']}: expected {expected}, engine returned {actual}")
        else:
            notes.append(f"{gate['key']}: {actual} (matches)")
    return ok, notes


def main() -> int:
    cases = load_cases()
    total = passed = skipped = failed = 0
    for case in cases:
        case_id = case["case_id"]
        if case.get("disputed"):
            print(f"[--] {case_id}: SKIPPED (disputed -- needs a human/expert decision, not a code check)")
            skipped += 1
            continue
        if not case.get("synthetic_facility_row"):
            print(f"[--] {case_id}: SKIPPED (no synthetic_facility_row -- not a facility-level MUST-gate case)")
            skipped += 1
            continue
        total += 1
        ok, notes = run_case(case)
        status = "PASS" if ok else "MISMATCH"
        marker = "[OK]" if ok else "[XX]"
        print(f"{marker} {case_id}: {status}")
        for note in notes:
            print(f"    {note}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed}/{total} checkable cases match the engine's current behavior ({skipped} skipped).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
