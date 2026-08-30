"""Step 2 of the gold-dataset methodology: run the real engine (evaluate_candidate_intent)
against a resident persona x every real facility in the canonical registry, and bucket the
results. This produces *candidates* for the next batch of gold examples -- it does not
write gold examples itself. Every candidate still needs a human (and for MUST-gate policy
edge cases, a domain expert) to review before it becomes a nursing-gold-NNNN record; this
script's job is only to make "which 20-30 pairs are actually worth that review" a quick
scan instead of a guess.

Usage:
    cd backend && python gold_examples/screen_candidates.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as _boot  # noqa: F401 -- registers the meta_path import redirects
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.facility_parameter_service import _load_runtime


def _load_real_agent_evidence() -> Dict[str, list]:
    """Without this, every facility gets agent_person_fit_evidence=[] and the whole
    screen just reports the same structural default for all 377 -- not real variance.
    Batches one query for every AgentKnowledgeRecord instead of one per facility.
    """
    from sqlalchemy import inspect

    from app.database import SessionLocal
    from app.models.agent_execution import AgentKnowledgeRecord

    db = SessionLocal()
    try:
        if AgentKnowledgeRecord.__tablename__ not in inspect(db.get_bind()).get_table_names():
            print("(agent_knowledge_records table not present in this DB -- evidence will be empty)")
            return {}
        rows = db.query(AgentKnowledgeRecord.entity_key, AgentKnowledgeRecord.payload_json).all()
    finally:
        db.close()

    by_facility: Dict[str, list] = defaultdict(list)
    for entity_key, payload_json in rows:
        try:
            payload = json.loads(payload_json or "{}")
        except (TypeError, ValueError):
            continue
        by_facility[entity_key].append({"payload": payload})
    return by_facility

PERSONA = {
    "location_city": "Las Vegas",
    "natural_language_query": (
        "My mother is 90. Her husband died two months ago and she does not want to remain "
        "alone at home. She is mentally alert, has no dementia, is mobile, and otherwise "
        "functions independently, but she needs daily help with bathing, dressing and "
        "medication management. She enjoys classical music and being around other people. "
        "We are looking across the Las Vegas Valley with a total monthly housing-and-care "
        "budget up to $8,000."
    ),
}


def main() -> None:
    runtime = _load_runtime()
    strategy = {
        "signals": {"adl_support_needed": True, "medication_support_needed": True},
        "household": {},
    }
    human_context = {"signals": {}}
    intent = build_client_intent(
        {"locationCity": PERSONA["location_city"]},
        PERSONA["natural_language_query"],
        strategy,
        human_context,
    )
    print("MUST-haves detected for this persona:", [m["key"] for m in intent["must_haves"]])
    print()

    agent_evidence_by_facility = _load_real_agent_evidence()
    print(f"Loaded real agent evidence for {len(agent_evidence_by_facility)} facilities.\n")

    by_gate: Dict[str, Counter] = defaultdict(Counter)
    interesting: list[dict] = []

    for canonical_id, facility in runtime["canonical_by_id"].items():
        row = {
            "canonical_facility_id": canonical_id,
            "canonical_type": facility.get("canonical_type"),
            "city": facility.get("city"),
            "state": facility.get("state"),
            "agent_person_fit_evidence": agent_evidence_by_facility.get(canonical_id, []),
        }
        result = evaluate_candidate_intent(row, intent)

        for key in intent["must_haves"]:
            gate_key = key["key"]
            if gate_key in result["must_pass"]:
                status = "PASS"
            elif gate_key in result["must_fail"]:
                status = "FAIL"
            else:
                status = "PENDING_VERIFICATION"
            by_gate[gate_key][status] += 1

        # Flag facilities with a mixed PASS/PENDING result -- these are exactly the
        # "borderline" and "needs facility-side research" candidates the schema wants.
        statuses = {
            key["key"]: (
                "PASS" if key["key"] in result["must_pass"]
                else "FAIL" if key["key"] in result["must_fail"]
                else "PENDING_VERIFICATION"
            )
            for key in intent["must_haves"]
        }
        if "PASS" in statuses.values() and "PENDING_VERIFICATION" in statuses.values():
            interesting.append({
                "canonical_facility_id": canonical_id,
                "facility_name": facility.get("facility_name"),
                "canonical_type": facility.get("canonical_type"),
                "gate_statuses": statuses,
            })

    print(f"Screened {len(runtime['canonical_by_id'])} real facilities against this persona.\n")
    print("Per-gate outcome counts:")
    for gate_key, counts in by_gate.items():
        print(f"  {gate_key}: {dict(counts)}")

    print(f"\n{len(interesting)} facilities have a mixed PASS/PENDING_VERIFICATION profile")
    print("(candidates for the 'needs facility-side research' / borderline categories):")
    for row in interesting[:15]:
        print(f"  {row['canonical_facility_id']} | {row['facility_name']} | {row['gate_statuses']}")
    if len(interesting) > 15:
        print(f"  ... and {len(interesting) - 15} more")


if __name__ == "__main__":
    main()
