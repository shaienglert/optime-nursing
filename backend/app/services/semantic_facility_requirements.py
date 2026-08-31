from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.agent_execution import AgentQueueItem
from app.services import governed_evidence_runtime
from app.services.decision_agent_bridge import QUEUE_TYPE, _ensure_worker, _kick_worker_async, semantic_must_research_priority


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _semantic_result(result: Dict[str, Any]) -> Dict[str, Any]:
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    semantic_result = semantic.get("result") if isinstance(semantic.get("result"), dict) else {}
    return semantic_result


def extract_semantic_facility_requirements(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    statements = _semantic_result(result).get("statements") or []
    requirements: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        if _upper(statement.get("importance")) != "MUST" or _upper(statement.get("status")) != "RESEARCH_REQUIRED":
            continue
        if _upper(statement.get("knowledge_state")) != "KNOWN":
            continue
        mapped = [str(value or "").strip().lower() for value in statement.get("mapped_parameters") or []]
        haystack = " ".join(mapped + [str(statement.get("raw_text") or "").lower(), str(statement.get("meaning") or "").lower()])
        if any(token in haystack for token in ("gluten", "cross_contact", "cross-contact", "dietary", "allergy")):
            key, dimension = "SEMANTIC_DIETARY_SAFETY", "dietary_safety"
        elif any(token in haystack for token in ("all_daily_meals", "full_meal", "meal_plan", "all daily meals")):
            key, dimension = "SEMANTIC_ALL_DAILY_MEALS", "meal_service"
        elif any(token in haystack for token in ("walking", "route", "distance", "layout", "walker", "elevator", "rest_seat", "service_proximity")):
            key, dimension = "SEMANTIC_MOBILITY_LAYOUT", "mobility_layout"
        elif any(token in haystack for token in ("organized_activities", "isolation", "social", "card_games", "classes")):
            key, dimension = "SEMANTIC_SOCIAL_DELIVERY", "social_engagement"
        else:
            key, dimension = "SEMANTIC_FACILITY_EVIDENCE", "semantic_facility_evidence"
        if key in seen:
            continue
        seen.add(key)
        requirements.append({
            "key": key,
            "dimension": dimension,
            "reason": str(statement.get("meaning") or statement.get("raw_text") or "Material client MUST requires facility evidence."),
            "research_task": str(statement.get("research_task") or "Verify this requirement against current facility-specific evidence."),
            "mapped_parameters": mapped,
            "source": "SEMANTIC_AI_CLIENT_INTENT",
        })
    return requirements


def _payload_verifies(payload: Dict[str, Any], key: str) -> bool | None:
    if key == "SEMANTIC_MOBILITY_LAYOUT":
        value = payload.get("mobility_layout_verified")
    elif key == "SEMANTIC_DIETARY_SAFETY":
        value = payload.get("gluten_cross_contact_verified")
    elif key == "SEMANTIC_ALL_DAILY_MEALS":
        value = payload.get("all_daily_meals_verified")
    elif key == "SEMANTIC_SOCIAL_DELIVERY":
        value = payload.get("social_engagement_verified")
    else:
        value = None
    return value if isinstance(value, bool) else None


def _row_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return governed_evidence_runtime.agent_and_provider_payloads(row)


def _queue_requirement(row: Dict[str, Any], requirement: Dict[str, Any], candidate_rank_index: int = 0) -> bool:
    canonical_id = str(row.get("canonical_facility_id") or "").strip()
    if not canonical_id:
        return False
    dimension = str(requirement["dimension"])
    agent_key = "activities_intelligence" if dimension == "social_engagement" else "provider_intelligence"
    db = SessionLocal()
    try:
        _ensure_worker(db, agent_key)
        pending = db.query(AgentQueueItem).filter(
            AgentQueueItem.queue_type == QUEUE_TYPE,
            AgentQueueItem.agent_key == agent_key,
            AgentQueueItem.status.in_(["PENDING", "RUNNING"]),
        ).all()
        for item in pending:
            try:
                payload = json.loads(item.payload_json or "{}")
            except json.JSONDecodeError:
                continue
            if payload.get("canonical_facility_id") == canonical_id and payload.get("dimension") == dimension:
                return False
        payload = {
            "market": "las-vegas",
            "canonical_facility_id": canonical_id,
            "facility_name": row.get("facility_name"),
            "city": row.get("city") or "LAS VEGAS",
            "state": "NV",
            "dimension": dimension,
            "requested_parameters": requirement.get("mapped_parameters") or [],
            "semantic_requirement_key": requirement.get("key"),
            "semantic_research_task": requirement.get("research_task"),
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "research_priority": semantic_must_research_priority(candidate_rank_index),
        }
        db.add(AgentQueueItem(queue_type=QUEUE_TYPE, agent_key=agent_key, payload_json=json.dumps(payload, sort_keys=True), status="PENDING", max_attempts=3))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def apply_semantic_facility_requirements(result: Dict[str, Any], *, research_limit: int = 20) -> Dict[str, Any]:
    requirements = extract_semantic_facility_requirements(result)
    rows = list(result.get("results") or [])
    queued = 0
    if requirements:
        for index, row in enumerate(rows):
            fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
            passed = list(fit.get("must_pass") or [])
            unknown = list(fit.get("must_unknown") or [])
            failed = list(fit.get("must_fail") or [])
            payloads = _row_payloads(row)
            trace: List[Dict[str, Any]] = []
            for requirement in requirements:
                key = str(requirement["key"])
                # Never hard-fail entry on unverified agent evidence: decision_research_worker.py
                # stamps every *_verified field False by default on every research pass,
                # regardless of which specific dimension was actually requested, so a False
                # here is frequently "never researched for this requirement", not "confirmed
                # not offered". Matches the same policy already applied to the
                # ADL/MEDICATION/REHAB/RECOVERY_TRANSITION gates in client_intent_runtime.py:
                # agent evidence may only confirm a MUST (PASS), never exclude on it (FAIL).
                verdicts = [_payload_verifies(payload, key) for payload in payloads]
                if True in verdicts:
                    if key not in passed: passed.append(key)
                    status = "PASS"
                else:
                    if key not in unknown: unknown.append(key)
                    status = "UNKNOWN"
                    if index < research_limit and _queue_requirement(row, requirement, index):
                        queued += 1
                trace.append({**requirement, "status": status})
            fit["must_pass"] = passed
            fit["must_unknown"] = unknown
            fit["must_fail"] = failed
            fit["hard_gate"] = "FAIL" if failed else ("PENDING_VERIFICATION" if unknown else "PASS")
            fit["semantic_must_trace"] = trace
            row["client_intent_fit"] = fit
    if queued:
        _kick_worker_async()
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    decision["semantic_facility_requirements"] = {
        "requirements": requirements,
        "tasks_queued": queued,
        "rule": "Semantic AI identifies client MUSTs; facility evidence or direct verification decides PASS/FAIL. UNKNOWN never becomes PASS.",
    }
    if requirements and any((row.get("client_intent_fit") or {}).get("must_unknown") for row in rows):
        decision["decision_finality"] = "PROVISIONAL_PENDING_SEMANTIC_MUST_EVIDENCE"
        decision["recommendation_execution_allowed"] = False
    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_semantic_facility_requirements", "extract_semantic_facility_requirements"]
