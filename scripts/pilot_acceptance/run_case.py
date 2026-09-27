"""Run ONE acceptance case against the synthetic-pilot market in a fresh interpreter.

Usage: python run_case.py <case_key> <out_json>

Each case gets its own process and its own empty database so nothing carries between
cases. The whole pilot catalog is exposed, not the default first fifty, because a
benchmark that silently looks at a quarter of the market is not a benchmark.

The interview AI is used for real when a key is present. Without one it is pinned to a
fixed READY answer and the snapshot records `interview_ai: "MOCKED"`, so a run can never
be mistaken for one that exercised the live model.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

CASE = sys.argv[1]
OUT = Path(sys.argv[2])

TMP = Path(tempfile.mkdtemp(prefix="pilot_acceptance_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TMP / 'acceptance.db').as_posix()}"
os.environ["OPTIME_CANONICAL_MARKET"] = "synthetic-pilot"
os.environ.setdefault("OOMNIK_PILOT_FACILITY_LIMIT", "200")

sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(HERE))
logging.disable(logging.CRITICAL)

from cases import CASES  # noqa: E402
from oracle import grade  # noqa: E402

LIVE_AI = bool(str(os.getenv("OPTIME_SEMANTIC_AI_API_KEY") or "").strip())
FIXED_AI = {"decision_readiness": "READY", "next_question": None, "statements": []}


def main() -> int:
    case = CASES[CASE]
    patches = [patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False)]
    if not LIVE_AI:
        patches.append(patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
            return_value=FIXED_AI,
        ))
    for started in patches:
        started.start()

    from app.services.patient_decision_engine import build_patient_needs_profile, run_patient_decision_engine

    questionnaire, query = case["questionnaire"], case["query"]
    profile = build_patient_needs_profile(questionnaire, query)
    decision = run_patient_decision_engine(questionnaire, query, limit=5)

    intelligence = decision.get("decision_intelligence") or {}
    state = intelligence.get("canonical_decision_state") or {}
    pipeline = intelligence.get("facility_selection_pipeline") or {}
    intent = intelligence.get("client_intent") or {}

    snapshot = {
        "case": CASE,
        "title": case["title"],
        "interview_ai": "LIVE" if LIVE_AI else "MOCKED",
        "pilot_facility_limit": os.environ["OOMNIK_PILOT_FACILITY_LIMIT"],
        "phase": state.get("phase"),
        "can_show_recommendations": state.get("can_show_recommendations"),
        "next_action": state.get("next_action"),
        "scored": decision.get("total_candidates_scored"),
        "shown": decision.get("result_count"),
        "must_eligible": decision.get("must_eligible_count"),
        "must_pending": pipeline.get("must_pending_verification_count"),
        "must_rejected": pipeline.get("must_rejected_count"),
        "ai_ranking": (pipeline.get("ai_ranking") or {}).get("status"),
        "must_haves": [m.get("key") for m in (intent.get("must_haves") or [])],
        "household": ((intelligence.get("living_strategy") or {}).get("household") or {}).get("type"),
        "candidate_discovery": decision.get("candidate_discovery"),
        "market_coverage_notice": decision.get("market_coverage_notice"),
        "needs": {
            str(need.get("parameter_id")): f'{need.get("requirement_level")}={need.get("desired_value")}'
            for need in (profile.get("needs") or []) if isinstance(need, dict)
        },
        "grade": grade(case, profile, decision),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0 if snapshot["grade"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
