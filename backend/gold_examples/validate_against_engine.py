"""Run the real governing engine for each gold example against its
`synthetic_facility_row`, and report whether the engine's actual verdict matches the
gold `must_gates` expectation. Which engine governs a case is its `engine` field
(default "client_intent_runtime" for cases predating this field):

- client_intent_runtime: the dynamic MUST gate (client_intent_runtime.evaluate_candidate_intent)
- semantic_facility_requirements: free-text client MUSTs with no standard key
  (mobility layout, dietary safety, all-daily-meals, social delivery); also needs
  `synthetic_semantic_statement`, the statement fed to extract_semantic_facility_requirements
- combined_care_solution_runtime: ADL/medication care-delivery coverage
  (build_combined_care_solution); checks medication_component/care_component depending
  on which key is in must_gates

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
from app.services.combined_care_solution_runtime import build_combined_care_solution
from app.services.semantic_facility_requirements import apply_semantic_facility_requirements

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


def _run_client_intent_runtime_case(case: dict) -> tuple[bool, list[str]]:
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


def _run_semantic_facility_requirements_case(case: dict) -> tuple[bool, list[str]]:
    row = dict(case["synthetic_facility_row"])
    statement = case["synthetic_semantic_statement"]
    payload = {
        "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {"statements": [statement]}}}},
        "results": [row],
    }
    out = apply_semantic_facility_requirements(payload)
    fit = out["results"][0]["client_intent_fit"]

    notes = []
    ok = True
    for gate in case["must_gates"]:
        actual = gate_status(fit, gate["key"])
        expected = gate["status"]
        if actual != expected:
            ok = False
            notes.append(f"{gate['key']}: expected {expected}, engine returned {actual}")
        else:
            notes.append(f"{gate['key']}: {actual} (matches)")
    return ok, notes


def _run_combined_care_solution_runtime_case(case: dict) -> tuple[bool, list[str]]:
    row = dict(case["synthetic_facility_row"])
    resident = case["resident"]
    result = build_combined_care_solution(row, {"locationCity": resident.get("location_city") or ""}, resident.get("natural_language_query") or "")

    notes = []
    ok = True
    for gate in case["must_gates"]:
        key = gate["key"]
        component = "medication_component" if key == "MEDICATION_SUPPORT_AVAILABLE" else "care_component"
        actual = result[component]["combined_must_coverage"]
        expected = gate["status"] if gate["status"] in {"PASS", "FAIL"} else "PENDING_VERIFICATION"
        if actual != expected:
            ok = False
            notes.append(f"{key}: expected {expected}, engine returned {actual}")
        else:
            notes.append(f"{key}: {actual} (matches)")
    return ok, notes


_ENGINE_RUNNERS = {
    "client_intent_runtime": _run_client_intent_runtime_case,
    "semantic_facility_requirements": _run_semantic_facility_requirements_case,
    "combined_care_solution_runtime": _run_combined_care_solution_runtime_case,
}


def run_case(case: dict) -> tuple[bool, list[str]]:
    engine = case.get("engine") or "client_intent_runtime"
    return _ENGINE_RUNNERS[engine](case)


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
