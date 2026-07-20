import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "database" / "validation_program_registry.json"
STATUS_PATH = ROOT / "reports" / "VALIDATION_PROGRAM_STATUS.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    registry = _load_json(REGISTRY_PATH)
    status = _load_json(STATUS_PATH)

    tracks = registry.get("validation_tracks", [])
    track_ids = {track.get("track_id") for track in tracks}
    if track_ids != {"MECHANICAL_RUNTIME", "EXTERNAL_PROFESSIONAL"}:
        errors.append("validation tracks must contain MECHANICAL_RUNTIME and EXTERNAL_PROFESSIONAL")

    status_tracks = {track.get("track_id") for track in status.get("tracks", [])}
    if status_tracks != track_ids:
        errors.append("status tracks must mirror registry tracks")

    mechanical_registry = registry.get("mechanical_validators", [])
    mechanical_status = status.get("mechanical", {}).get("validators", [])
    if len(mechanical_registry) != len(mechanical_status):
        errors.append("mechanical validator count mismatch between registry and status")

    required_failures = [
        row.get("id")
        for row in mechanical_status
        if row.get("required") and row.get("status") != "PASS"
    ]
    if required_failures:
        errors.append("required mechanical validator failures: " + ", ".join(str(x) for x in required_failures))

    if status.get("mechanical", {}).get("overall_status") != "PASS":
        errors.append("mechanical overall status must be PASS")

    external_summary = status.get("external", {}).get("summary", {})
    total = int(external_summary.get("total") or 0)
    complete = int(external_summary.get("complete") or 0)
    overall_external = str(status.get("external", {}).get("overall_status") or "")

    if total <= 0:
        errors.append("external validation summary total must be > 0")

    if complete < total and overall_external != "PARTIAL":
        errors.append("external status must be PARTIAL when not all external requirements are complete")

    if complete == 0:
        warnings.append("no external validation requirements are complete yet")

    if errors:
        print("SEPARATED_VALIDATION_PROGRAM=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("SEPARATED_VALIDATION_PROGRAM=PASS")
    print("MECHANICAL_TRACK=PASS")
    print("EXTERNAL_TRACK=PASS")
    print(f"EXTERNAL_TOTAL={total}")
    print(f"EXTERNAL_COMPLETE={complete}")
    if warnings:
        print("SEPARATED_VALIDATION_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("SEPARATED_VALIDATION_WARNINGS=NO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
