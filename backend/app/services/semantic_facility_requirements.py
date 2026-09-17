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


def extract_semantic_facility_requirements(result: Dict[str, Any], questionnaire_state: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    requirements: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # A budget stated only in the structured questionnaire field (no matching
    # free-text mention) never reaches Semantic AI's statements at all -- and stays
    # invisible even when the AI call fails outright for an unrelated reason, since
    # this check has no dependency on it succeeding. A client-stated monthly budget,
    # in any form, always requires facility-side price verification.
    budget = (questionnaire_state or {}).get("budget")
    if budget not in (None, "", 0):
        seen.add("SEMANTIC_BUDGET_VERIFICATION")
        requirements.append({
            "key": "SEMANTIC_BUDGET_VERIFICATION",
            "dimension": "budget_verification",
            "reason": "A stated monthly budget requires facility-specific price verification.",
            "research_task": "Verify this requirement against current facility-specific evidence.",
            "mapped_parameters": ["budget"],
            "source": "QUESTIONNAIRE_CLIENT_INTENT",
        })

    statements = _semantic_result(result).get("statements") or []
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        if _upper(statement.get("importance")) != "MUST":
            continue
        if _upper(statement.get("knowledge_state")) != "KNOWN":
            continue
        mapped = [str(value or "").strip().lower() for value in statement.get("mapped_parameters") or []]
        statement_text = " ".join([
            str(statement.get("raw_text") or "").lower(),
            str(statement.get("meaning") or "").lower(),
        ])
        haystack = " ".join(mapped + [statement_text])
        # A model-selected questionnaire mapping is not proof that the client
        # requested a future-care continuum.  Require the client's statement
        # (or its semantic meaning) to say so explicitly.  This prevents a
        # current memory-care need or pending Medicaid status from being
        # converted into an unrelated continuum-of-care MUST.
        future_care = any(token in statement_text for token in (
            "futurecare", "future_care", "future-care", "continuum", "aginginplace",
            "future care", "aging in place", "aging_in_place", "avoid future moves",
            "avoidfuturemoves", "avoid_future_moves", "life plan",
        ))
        if future_care:
            key, dimension = "SEMANTIC_FUTURE_CARE_PATH", "recovery_transition"
        elif "kosher" in haystack:
            key, dimension = "SEMANTIC_KOSHER_DIET", "kosher_diet"
        elif any(token in haystack for token in ("gluten", "cross_contact", "cross-contact", "dietary", "allergy")):
            key, dimension = "SEMANTIC_DIETARY_SAFETY", "dietary_safety"
        elif any(token in haystack for token in ("all_daily_meals", "full_meal", "meal_plan", "all daily meals")):
            key, dimension = "SEMANTIC_ALL_DAILY_MEALS", "meal_service"
        elif any(token in haystack for token in ("walking", "route", "distance", "layout", "walker", "elevator", "rest_seat", "service_proximity")):
            key, dimension = "SEMANTIC_MOBILITY_LAYOUT", "mobility_layout"
        elif any(token in haystack for token in ("organized_activities", "isolation", "social", "card_games", "classes")):
            key, dimension = "SEMANTIC_SOCIAL_DELIVERY", "social_engagement"
        elif any(token in haystack for token in (
            "dialysis", "wound_care", "wound care", "nursing_support", "medical_complexity",
            "clinical_acuity", "skilled_nursing_need", "iv_therapy", "catheter", "ventilator",
            "tracheostomy", "oxygen_support", "complex medical",
        )):
            key, dimension = "SEMANTIC_CLINICAL_ACUITY", "clinical_acuity"
        elif any(token in haystack for token in (
            "primary_language", "language_access", "preferred_language", "language_support",
            "hebrew", "speak her language", "speak his language",
        )):
            key, dimension = "SEMANTIC_LANGUAGE_SUPPORT", "language_support"
        elif any(token in haystack for token in (
            "budget", "afford", "monthly_affordability", "published_rates", "total_monthly_cost",
        )):
            # No facility in this system's evidence schema carries a verified monthly
            # rate yet (the supplier database has 0 fully-verified pricing records as of
            # this writing) -- so this requirement will land in must_unknown and stay
            # there until real pricing data exists. That is the correct, honest outcome:
            # a stated budget must stop a false PASS/FINAL recommendation, not silently
            # become a mere "prefer transparent pricing" preference as it was before.
            key, dimension = "SEMANTIC_BUDGET_VERIFICATION", "budget_verification"
        elif "medicaid" in haystack:
            key, dimension = "SEMANTIC_MEDICAID_PATHWAY", "medicaid_pathway"
        else:
            key, dimension = "SEMANTIC_FACILITY_EVIDENCE", "semantic_facility_evidence"
        # Every recognized facility-capability bucket above is a governed domain this
        # module knows how to route to research and verify -- a client MUST landing in
        # one of them must survive to the gate even when Semantic AI marks it USED
        # (client-side understanding is settled; facility-side verification is not).
        # An unrecognized statement (the generic SEMANTIC_FACILITY_EVIDENCE bucket) has
        # no known verification path, so it stays on the original, more conservative
        # RESEARCH_REQUIRED-only trigger rather than being promoted blind.
        recognized_capability_bucket = key != "SEMANTIC_FACILITY_EVIDENCE"
        status = _upper(statement.get("status"))
        if status != "RESEARCH_REQUIRED" and not (recognized_capability_bucket and status == "USED"):
            continue
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
    if key == "SEMANTIC_FUTURE_CARE_PATH":
        # A same-apartment transition only says that some support can be added
        # without changing units.  It does not prove that the community offers
        # a real progression of care levels.  Treating it as a continuum made
        # independent-only housing look like a verified future-care pathway.
        if payload.get("continuum_of_care_verified") is True:
            return True
        return None
    if key == "SEMANTIC_MOBILITY_LAYOUT":
        value = payload.get("mobility_layout_verified")
    elif key == "SEMANTIC_DIETARY_SAFETY":
        value = payload.get("gluten_cross_contact_verified")
    elif key == "SEMANTIC_ALL_DAILY_MEALS":
        value = payload.get("all_daily_meals_verified")
    elif key == "SEMANTIC_SOCIAL_DELIVERY":
        value = payload.get("social_engagement_verified")
    elif key == "SEMANTIC_CLINICAL_ACUITY":
        value = payload.get("clinical_acuity_verified")
    elif key == "SEMANTIC_KOSHER_DIET":
        value = payload.get("kosher_verified")
    elif key == "SEMANTIC_LANGUAGE_SUPPORT":
        value = payload.get("language_support_verified")
    elif key == "SEMANTIC_BUDGET_VERIFICATION":
        value = payload.get("published_rates_verified")
    elif key == "SEMANTIC_MEDICAID_PATHWAY":
        value = payload.get("medicaid_accepted_verified")
    else:
        value = None
    return value if isinstance(value, bool) else None


def _row_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return governed_evidence_runtime.agent_and_provider_payloads(row)


def _row_verifies_future_care(row: Dict[str, Any]) -> bool:
    """Accept continuum proof only from the evidence record that owns that claim.

    Agent research records contain model-interpreted snapshots and are useful for
    deciding what Oomnik should verify next, but they are not authoritative enough
    to settle this safety-relevant MUST. Provider-curated primary evidence or an
    explicit life-plan modality are the only positive paths here.
    """
    provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
    evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else {}
    if evidence.get("continuum_of_care_verified") is True:
        return True

    modalities = {_upper(value) for value in row.get("housing_modalities") or []}
    if "LIFE_PLAN_CCRC" in modalities:
        return True

    return False


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


def apply_semantic_facility_requirements(result: Dict[str, Any], *, research_limit: int = 20, questionnaire_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    requirements = extract_semantic_facility_requirements(result, questionnaire_state)
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
                # This function runs before and after asynchronous research.  A
                # previous pass must never survive a later evidence refresh.
                passed = [value for value in passed if value != key]
                unknown = [value for value in unknown if value != key]
                failed = [value for value in failed if value != key]
                # Never hard-fail entry on unverified agent evidence: decision_research_worker.py
                # stamps every *_verified field False by default on every research pass,
                # regardless of which specific dimension was actually requested, so a False
                # here is frequently "never researched for this requirement", not "confirmed
                # not offered". Matches the same policy already applied to the
                # ADL/MEDICATION/REHAB/RECOVERY_TRANSITION gates in client_intent_runtime.py:
                # agent evidence may only confirm a MUST (PASS), never exclude on it (FAIL).
                verdicts = [_payload_verifies(payload, key) for payload in payloads]
                verified = _row_verifies_future_care(row) if key == "SEMANTIC_FUTURE_CARE_PATH" else True in verdicts
                if verified:
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
    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_semantic_facility_requirements", "extract_semantic_facility_requirements"]
