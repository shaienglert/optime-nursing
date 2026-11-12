"""Run all golden HTTP-contract cases in isolated subprocesses; fail build if any fails."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE / "pilot_acceptance"))
from cases import CASES

failed=[]
for index, case in enumerate(CASES,1):
    print(f"HTTP_ACCEPTANCE_START {index}/{len(CASES)} {case}",flush=True)
    try:
        proc=subprocess.run([sys.executable,str(HERE / "p0_http_acceptance.py"),case],
                            timeout=300,check=False)
        code=proc.returncode
    except subprocess.TimeoutExpired:
        code=124
    print(f"HTTP_ACCEPTANCE_END {case} exit={code}",flush=True)
    if code!=0:
        failed.append(case)
print(f"HTTP_ACCEPTANCE_SUMMARY total={len(CASES)} passed={len(CASES)-len(failed)} failed={len(failed)} cases={failed}",flush=True)
raise SystemExit(1 if failed else 0)
