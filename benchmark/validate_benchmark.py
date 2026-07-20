from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def has_secret_like_value(text: str) -> bool:
    patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"AIza[0-9A-Za-z\-_]{20,}",
        r"pplx-[A-Za-z0-9]{16,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def validate(case_manifest: dict[str, Any], case_registry: dict[str, Any], run_payload: dict[str, Any], blind_payload: dict[str, Any], scorecards: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    manifest_index = {(row["case_id"], row["version"]): row["content_hash"] for row in case_manifest.get("entries", [])}
    for case in case_registry.get("cases", []):
        key = (case["case_id"], case["version"])
        if key not in manifest_index:
            errors.append(f"Case {case['case_id']} missing from freeze manifest")

    records = run_payload.get("records", [])
    hash_by_track_case: dict[tuple[str, str], set[str]] = {}

    for record in records:
        track = record.get("track")
        case_id = record.get("case_id")
        key = (track, case_id)
        hash_by_track_case.setdefault(key, set()).add(record.get("prompt", {}).get("prompt_hash"))

        raw = record.get("raw_response", {})
        normalized = record.get("normalized_response", {})
        if not raw:
            errors.append(f"Raw response missing for {record.get('provider')} {track}")
        if raw.get("response_text") in (None, "") and raw.get("response_json") in (None, {}):
            errors.append(f"Raw response payload empty for {record.get('provider')} {track}")
        if normalized and not raw:
            errors.append(f"Normalized exists but raw missing for {record.get('provider')} {track}")

        if record.get("provider") == "optime":
            model_version = str(raw.get("model_version", ""))
            status = raw.get("run_status")
            fixture_label = raw.get("fixture_label")
            if "optime-v2-engine.ts" not in model_version and status != "CHAIN_BREAK" and fixture_label != "TEST_FIXTURE_NOT_REAL_AI_RESULT":
                errors.append("OPTIME adapter appears to bypass runtime engine path")

        if track not in {"TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"}:
            errors.append("Track label missing or invalid")

        blob = json.dumps(record, ensure_ascii=True)
        if has_secret_like_value(blob):
            errors.append(f"Potential secret detected in run artifact for {record.get('provider')}")

        for case in case_registry.get("cases", []):
            if case.get("origin") == "SYNTHETIC" and str(case.get("defined_by", "")).upper().find("EXTERNAL") >= 0:
                errors.append(f"Synthetic case mislabeled as external in {case.get('case_id')}")

        claims = record.get("claim_source_audit", [])
        for claim in claims:
            if claim.get("supports_claim") is False and claim.get("conflict_status") == "FALSE_BY_DEFAULT":
                errors.append("Unverifiable claim automatically marked false")

    for key, hashes in hash_by_track_case.items():
        if len(hashes) != 1:
            errors.append(f"Prompt parity failed for {key[0]} {key[1]}")

    for item in blind_payload.get("blind_packet", []):
        if item.get("provider") != "REDACTED" or item.get("model") != "REDACTED":
            errors.append("Provider identity leaked in blind packet")

    instructions = blind_payload.get("judge_instructions", {})
    if not instructions.get("no_identity_exposure", False):
        errors.append("Blind judge governance missing no_identity_exposure")

    if scorecards.get("composite_score") is not None and not scorecards.get("composite_weights_documented", False):
        errors.append("Composite score uses undocumented weights")

    return sorted(set(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate benchmark governance constraints")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    case_manifest = load_json(root / "benchmark" / "cases" / "case_freeze_manifest.json")
    case_registry = load_json(root / "database" / "benchmark_cases.json")
    run_payload = load_json(root / "benchmark" / "runs" / f"benchmark_run_{args.run_id}.json")
    blind_payload = load_json(root / "benchmark" / "runs" / f"blind_packet_{args.run_id}.json")
    scorecards = load_json(root / "benchmark" / "runs" / f"scorecards_{args.run_id}.json")

    errors = validate(case_manifest, case_registry, run_payload, blind_payload, scorecards)
    output = {
        "run_id": args.run_id,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }

    out_path = root / "benchmark" / "runs" / f"validation_{args.run_id}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
