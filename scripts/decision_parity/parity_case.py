"""Run ONE parity case in a fresh interpreter and dump a normalized JSON snapshot.

Invoked by run_parity.py: python parity_case.py <repo_backend_dir> <case_name> <out_json>

Everything the decision engine exposes is captured:
  * direct library calls (run_patient_decision_engine at two limits,
    build_patient_needs_profile, build_patient_comparison_context)
  * the FastAPI endpoints (/decision-engine/patient-needs-profile,
    /decision-engine/recommendations, /decision-engine/comparison-context)
  * every database row the run wrote (side effects), per table

AI boundaries are made deterministic: the interview AI is mocked to a fixed answer
(same pattern the repo's own tests use) and no API key is present, so every other
semantic-AI stage takes its governed "unavailable" path.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(sys.argv[1]).resolve()
CASE = sys.argv[2]
OUT = Path(sys.argv[3])

TMP = Path(tempfile.mkdtemp(prefix="parity_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TMP / 'parity.db').as_posix()}"
os.environ.pop("OPTIME_SEMANTIC_AI_API_KEY", None)
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).parent))

from cases import CASES  # noqa: E402

case = CASES[CASE]
os.environ["OPTIME_CANONICAL_MARKET"] = case.get("market", "las-vegas")
for key, value in case.get("env", {}).items():
    os.environ[key] = value

import logging  # noqa: E402

logging.disable(logging.CRITICAL)

VOLATILE_KEY = re.compile(r"(_ms$|^ms$|duration|elapsed|latency|timestamp|generated_at|created_at|updated_at|loaded_at|requested_at|queued_at|observed_at_utc|run_id|request_id|trace_id|^id$|uuid|swap_count|last_swap_reason|perf_counter|^catalog_version$|^runtime_version$|artifact_signature|^decision_id$|^intake_profile_id$|^token_hash$|^created_at_epoch$|^expires_at_epoch$)", re.I)
ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)?")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
MEM_ID = re.compile(r"ROW-\d+|id=\d{6,}|(?<=decision:)[0-9a-f]{24}(?=:)")


def norm(value):
    if isinstance(value, dict):
        return {k: ("<volatile>" if VOLATILE_KEY.search(str(k)) else norm(v)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [norm(v) for v in value]
    if isinstance(value, str):
        value = ISO_TS.sub("<ts>", value)
        value = UUID.sub("<uuid>", value)
        value = MEM_ID.sub("<memid>", value)
        value = value.replace(str(TMP), "<tmp>")
        return value
    if isinstance(value, float):
        return round(value, 9)
    return value


def _all_rows():
    from sqlalchemy import inspect, text

    from app.database import engine

    tables = {}
    with engine.connect() as conn:
        for name in sorted(inspect(conn).get_table_names()):
            rows = [dict(r._mapping) for r in conn.execute(text(f'SELECT * FROM "{name}"'))]
            rows = [norm({k: (json.loads(v) if isinstance(v, str) and v[:1] in "[{" else v) for k, v in r.items()}) for r in rows]
            tables[name] = [json.dumps(r, sort_keys=True, default=str) for r in rows]
    return tables


def dump_db(before):
    """Rows the case added after app startup (startup seeding is excluded)."""
    after = _all_rows()
    out = {}
    for name, rows in after.items():
        prior = list(before.get(name, []))
        added = []
        for r in rows:
            if r in prior:
                prior.remove(r)
            else:
                added.append(r)
        if added:
            out[name] = [json.loads(r) for r in sorted(added)]
    return out


def _freeze_background_threads():
    """Background schedulers/research workers race with the request and make runs
    irreproducible. Parity must compare the request path only, so named daemon
    threads are not started. Request-scoped ThreadPoolExecutor workers still run."""
    import threading

    original_start = threading.Thread.start
    frozen = ("optime-", "agent-", "executive-", "oomnik-")

    def start(self, *a, **k):
        if self.daemon and str(self.name).startswith(frozen):
            FROZEN_THREADS.append(self.name)
            return None
        return original_start(self, *a, **k)

    threading.Thread.start = start


FROZEN_THREADS = []


def main():
    _freeze_background_threads()
    ai_result = case.get("interview_ai", {"decision_readiness": "READY", "next_question": None, "statements": []})
    patches = [
        patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False),
        patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result),
    ]
    if case.get("verified_rates"):
        patches.append(patch("app.services.governed_evidence_runtime.agent_and_provider_payloads", return_value=[{"published_rates_verified": True}]))
    for p in patches:
        p.start()

    snapshot = {}
    import app.main as main_module  # noqa: F401  -- same import order as production
    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    client.__enter__()  # run the production startup hook (schema + Nevada facility import)
    before = _all_rows()
    from app.services.patient_decision_engine import (
        build_patient_comparison_context,
        build_patient_needs_profile,
        run_patient_decision_engine,
    )

    q, text_ = case["questionnaire"], case["query"]
    snapshot["profile"] = build_patient_needs_profile(q, text_)
    snapshot["run_limit5"] = run_patient_decision_engine(q, text_, limit=5)
    snapshot["run_limit50"] = run_patient_decision_engine(q, text_, limit=50)
    ids = [r.get("canonical_facility_id") for r in (snapshot["run_limit50"].get("results") or [])][:3]
    if len(ids) >= 2:
        snapshot["comparison"] = build_patient_comparison_context(ids, snapshot["profile"])

    body = {"questionnaire_state": q, "natural_language_query": text_, "limit": 5}
    r1 = client.post("/decision-engine/patient-needs-profile", json={"questionnaire_state": q, "natural_language_query": text_})
    r2 = client.post("/decision-engine/recommendations", json=body)
    snapshot["http_profile"] = {"status": r1.status_code, "body": r1.json()}
    snapshot["http_recommendations"] = {"status": r2.status_code, "body": r2.json()}
    if len(ids) >= 2:
        r3 = client.post("/decision-engine/comparison-context", json={"canonical_facility_ids": ids, "patient_needs_profile": snapshot["profile"]})
        snapshot["http_comparison"] = {"status": r3.status_code, "body": r3.json()}

    snapshot["db_side_effects"] = dump_db(before)
    OUT.write_text(json.dumps(norm(snapshot), indent=1, sort_keys=True, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
