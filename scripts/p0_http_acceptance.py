"""HTTP-contract acceptance smoke, isolated only. Does not touch production data."""
from __future__ import annotations
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend"), str(ROOT / "scripts" / "pilot_acceptance")]
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.mkdtemp(prefix="oomnik_p0_api_")) / "validation.db")
os.environ["OPTIME_CANONICAL_MARKET"] = "synthetic-pilot"
os.environ["OOMNIK_PILOT_CATALOG_SIZE"] = "500"
os.environ["OOMNIK_PILOT_FACILITY_LIMIT"] = "500"
os.environ["OOMNIK_ISOLATED_TEST_MODE"] = "1"
os.environ["OPTIME_SEMANTIC_AI_ENABLED"] = "1"
os.environ["OPTIME_SEMANTIC_AI_REQUIRED"] = "1"

from cases import CASES
from oracle import grade

FIXED_AI = {"decision_readiness": "READY", "next_question": None, "statements": []}

async def run(case_id: str) -> bool:
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.patient_decision_engine import build_patient_needs_profile
    case = CASES[case_id]
    questionnaire = case["questionnaire"]
    query = case["query"]
    with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=FIXED_AI):
        await app.router._startup()
        try:
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://isolated.test", timeout=180) as client:
                health = await client.get("/health")
                runtime = await client.get("/runtime/status")
                result = await client.post("/decision-engine/recommendations", json={
                    "questionnaire_state": questionnaire,
                    "natural_language_query": query,
                    "limit": 5,
                })
                if result.status_code != 200:
                    print(json.dumps({"case":case_id,"status":result.status_code,"body":result.text[:900]}),flush=True)
                    return False
                output = result.json()
                profile = build_patient_needs_profile(questionnaire, query)
                report = grade(case, profile, output)
                meta = runtime.json().get("runtime_cache",{})
                passed = (health.status_code == 200 and meta.get("catalog_count") == 500
                          and report["passed"])
                print(json.dumps({
                    "case":case_id, "passed":passed, "http_status":result.status_code,
                    "catalog_count":meta.get("catalog_count"),
                    "shown":len(output.get("results") or []),
                    "failures":report["failures"],
                    "ai":"MOCKED_INTERVIEW_ONLY"
                }),flush=True)
                return passed
        finally:
            await app.router._shutdown()

if __name__ == "__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in CASES:
        raise SystemExit("Usage: python scripts/p0_http_acceptance.py CASE_ID")
    raise SystemExit(0 if asyncio.run(run(sys.argv[1])) else 1)
