import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "database" / "validation_program_registry.json"
OUTPUT_PATH = ROOT / "reports" / "VALIDATION_PROGRAM_STATUS.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_validator(script_path: str) -> dict:
    full_path = ROOT / script_path
    if not full_path.exists():
        return {
            "status": "FAIL",
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Script not found: {script_path}",
        }

    cmd = [str(ROOT / ".venv" / "Scripts" / "python.exe"), str(full_path)]
    completed = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    registry = _load_json(REGISTRY_PATH)
    mechanical = registry.get("mechanical_validators", [])
    external = registry.get("external_validation_requirements", [])

    mechanical_results = []
    mechanical_pass = True

    for validator in mechanical:
        result = _run_validator(str(validator.get("script")))
        mechanical_results.append(
            {
                "id": validator.get("id"),
                "script": validator.get("script"),
                "required": bool(validator.get("required")),
                **result,
            }
        )
        if bool(validator.get("required")) and result["status"] != "PASS":
            mechanical_pass = False

    external_summary = {
        "total": len(external),
        "pending": sum(1 for item in external if item.get("status") == "PENDING"),
        "not_available": sum(1 for item in external if item.get("status") == "NOT_AVAILABLE"),
        "complete": sum(1 for item in external if item.get("status") == "COMPLETE"),
    }

    payload = {
        "generated_at_utc": _utc_now(),
        "phase": 8,
        "tracks": registry.get("validation_tracks", []),
        "mechanical": {
            "overall_status": "PASS" if mechanical_pass else "FAIL",
            "validators": mechanical_results,
        },
        "external": {
            "overall_status": "PARTIAL" if external_summary["complete"] < external_summary["total"] else "COMPLETE",
            "requirements": external,
            "summary": external_summary,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"WROTE={OUTPUT_PATH}")
    print(f"MECHANICAL_OVERALL={payload['mechanical']['overall_status']}")
    print(f"EXTERNAL_OVERALL={payload['external']['overall_status']}")

    return 0 if mechanical_pass else 1


if __name__ == "__main__":
    sys.exit(main())
