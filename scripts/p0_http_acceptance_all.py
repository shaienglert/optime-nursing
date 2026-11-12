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
# Positive advisor gate: a governed NICE change can add two verified options,
# but injected MUST relaxations, invented numbers and auto-mutation must not pass.
sys.path.insert(0, str(HERE.parent / "backend"))
from app.services.oomniker_ai import advise_with_ai
governed = {"parameter": "COMMUNITY_ENVIRONMENT_MATCH", "authority": "PREFERENCE",
            "action": "OFFER_PREFERENCE_ALTERNATIVE", "new_recommendation_count": 2,
            "requires_client_approval": True, "may_auto_change": False,
            "message": "Two measured alternatives meet your required care needs.",
            "candidates": [{"canonical_facility_id": "pilot-A"}, {"canonical_facility_id": "pilot-B"}]}
advice = advise_with_ai(analysis={"suggestions": [governed]}, client_context={},
                         client_message="Can we keep every required care need?",
                         transport=lambda _: {"mode": "EXPLAIN_REQUIREMENTS",
                             "proposals": [{"parameter": "SECURED_UNIT_AVAILABLE"},
                                           {"parameter": "COMMUNITY_ENVIRONMENT_MATCH"}]})
advisor_pass = (advice.get("status") == "AI_ADVISORY_READY"
                and advice.get("proposals") == [governed]
                and advice.get("profile_mutated") is False
                and "Two measured alternatives" in advice.get("message", "")
                and "SECURED_UNIT_AVAILABLE" not in advice.get("message", ""))
print(f"OOMNIKER_POSITIVE_CONTRACT {'PASS' if advisor_pass else 'FAIL'}",flush=True)
if not advisor_pass:
    failed.append("oomniker_positive_contract")
print(f"HTTP_ACCEPTANCE_SUMMARY total={len(CASES)} passed={len(CASES)-len([f for f in failed if f in CASES])} failed={len(failed)} cases={failed}",flush=True)
raise SystemExit(1 if failed else 0)
