import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

VALIDATORS = [
    "scripts/validate_professional_rule_governance.py",
    "scripts/validate_three_layer_decision_model.py",
    "scripts/validate_facility_evidence_matrix.py",
    "scripts/validate_candidate_governance.py",
    "scripts/validate_top5_decision_table.py",
    "scripts/validate_recommendation_traceability.py",
    "scripts/validate_separated_validation_program.py",
]


def run_one(script: str):
    cmd = [str(PYTHON), str(ROOT / script)]
    completed = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    status = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"{script}={status}")
    if completed.stdout:
        for line in completed.stdout.strip().splitlines():
            print(f"  {line}")
    if completed.stderr:
        for line in completed.stderr.strip().splitlines():
            print(f"  STDERR: {line}")
    return completed.returncode == 0


def main() -> int:
    all_pass = True
    for script in VALIDATORS:
        ok = run_one(script)
        all_pass = all_pass and ok

    print(f"PHASE2_TO_8_BUNDLE={'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
