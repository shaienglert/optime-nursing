from __future__ import annotations

"""Governed AI process owner for the full Nursing decision lifecycle.

The same logical Semantic AI owner that drives clarification also owns the next step
once governed facility evidence exists. Rules/Guardian remain the authority for facts,
eligibility, MUST gates and safety. The AI may synthesize conclusions, compare governed
options and propose the next action, but it may not invent facility facts or introduce
candidate identities that are not present in the governed result.
"""

import os
from typing import Any, Dict, List

from app.services.semantic_intent_ai import _default_transport


_ALLOWED_PHASES = {"DISCOVERY", "CLARIFICATION", "RESEARCH", "COMPARE", "RECOMMEND", "FOLLOW_UP"}
_ALLOWED_ACTIONS = {"ASK_CLIENT", "RESEARCH_FACILITY_FACTS", "COMPARE_OPTIONS", "PRESENT_RECOMMENDATION", "VERIFY_BEFORE_DECISION", "FOLLOW_UP"}


def _candidate_packet(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    packet: List[Dict[str, Any]] = []
    for row in result.get("results") or []:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        care = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
        packet.append({
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "canonical_type": row.get("canonical_type"),
            "housing_modalities": row.get("housing_modalities") or [],
            "rank_position": row.get("rank_position"),
            "care_setting_fit": care,
            "client_intent_fit": {
                "hard_gate": fit.get("hard_gate"),
                "must_pass": fit.get("must_pass") or [],
                "must_unknown": fit.get("must_unknown") or [],
                "nice_match": fit.get("nice_match") or [],
            },
            "combined_care_solution": row.get("combined_care_solution") or {},
            "care_partner_access": row.get("care_partner_access") or {},
            "regulatory_history": row.get("regulatory_history") or {},
            "public_reputation": fit.get("public_reputation") or {},
        })
    return packet


def _phase(result: Dict[str, Any]) -> str:
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    readiness = str(human.get("decision_readiness") or decision.get("decision_readiness") or "UNKNOWN").upper()
    if readiness == "NEEDS_CLARIFICATION":
        return "CLARIFICATION"
    if readiness == "NEEDS_RESEARCH":
        return "RESEARCH"
    if decision.get("recommendation_execution_allowed") is not True:
        return "RESEARCH"
    finality = str(decision.get("decision_finality") or "UNKNOWN").upper()
    if "PENDING" in finality or "PROVISIONAL" in finality or "INCOMPLETE" in finality:
        return "RESEARCH"
    if len(result.get("results") or []) > 1:
        return "COMPARE"
    return "RECOMMEND"


def _prompt(result: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    patient = result.get("patient_needs_profile") if isinstance(result.get("patient_needs_profile"), dict) else {}
    phase = _phase(result)
    return {
        "role": "OPTIME_NURSING_AI_PROCESS_OWNER",
        "mission": "Own the resident/family decision process from understanding through recommendation and follow-up. Decide what should happen next, derive conclusions only from governed evidence, and propose practical solutions without inventing facts.",
        "process_phase": phase,
        "rules": [
            "You are the process owner; Guardian/rules constrain and validate but do not manage the conversation.",
            "Use only facts present in the supplied governed packet. UNKNOWN remains UNKNOWN.",
            "Never invent facility capability, price, availability, reputation, regulatory status or care-partner facts.",
            "Never introduce a facility ID or name that is absent from governed_candidates.",
            "A MUST failure can never be recommended around.",
            "A material MUST unknown requires verification before a final recommendation.",
            "Explain the actual trade-off and propose the complete solution, including housing plus external care when that is the governed strategy.",
            "Choose exactly one next_best_action that advances the process most.",
            "If the client must answer something, ASK_CLIENT. If the missing fact belongs to a provider/facility, RESEARCH_FACILITY_FACTS.",
            "When evidence is sufficient, PRESENT_RECOMMENDATION and explain why it is preferable to alternatives.",
            "Do not stop at a ranking: state conclusions, proposed solutions and the next step.",
        ],
        "original_user_request": natural_language_query,
        "questionnaire_state": questionnaire_state,
        "patient_needs_profile": {
            "needs": patient.get("needs") or [],
            "location_city": patient.get("location_city"),
            "living_strategy": patient.get("living_strategy") or {},
            "client_intent": patient.get("client_intent") or {},
        },
        "decision_state": {
            "decision_finality": decision.get("decision_finality"),
            "recommendation_execution_allowed": decision.get("recommendation_execution_allowed"),
            "strategy_universe": decision.get("strategy_universe") or {},
            "care_partner_layer": decision.get("care_partner_layer") or {},
            "must_gate": decision.get("must_gate") or {},
            "ranking_order": decision.get("ranking_order") or [],
        },
        "governed_candidates": _candidate_packet(result),
        "required_output": {
            "process_phase": "DISCOVERY|CLARIFICATION|RESEARCH|COMPARE|RECOMMEND|FOLLOW_UP",
            "process_summary": "string",
            "conclusions": [{"conclusion": "string", "evidence_facility_ids": ["string"]}],
            "proposed_solutions": [{"solution": "string", "facility_ids": ["string"], "why": "string", "verification_needed": ["string"]}],
            "next_best_action": {"action": "ASK_CLIENT|RESEARCH_FACILITY_FACTS|COMPARE_OPTIONS|PRESENT_RECOMMENDATION|VERIFY_BEFORE_DECISION|FOLLOW_UP", "reason": "string", "question": "string|null", "research_tasks": ["string"]},
            "follow_up_plan": ["string"],
        },
    }


def _validate(packet: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    phase = str(packet.get("process_phase") or "").upper()
    if phase not in _ALLOWED_PHASES:
        raise RuntimeError(f"AI_PROCESS_OWNER_INVALID_PHASE:{phase}")
    action_packet = packet.get("next_best_action") if isinstance(packet.get("next_best_action"), dict) else {}
    action = str(action_packet.get("action") or "").upper()
    if action not in _ALLOWED_ACTIONS:
        raise RuntimeError(f"AI_PROCESS_OWNER_INVALID_ACTION:{action}")
    allowed_ids = {str(row.get("canonical_facility_id") or "") for row in result.get("results") or [] if row.get("canonical_facility_id")}
    referenced: set[str] = set()
    for item in packet.get("conclusions") or []:
        if isinstance(item, dict):
            referenced.update(str(v) for v in item.get("evidence_facility_ids") or [] if str(v))
    for item in packet.get("proposed_solutions") or []:
        if isinstance(item, dict):
            referenced.update(str(v) for v in item.get("facility_ids") or [] if str(v))
    foreign = sorted(referenced - allowed_ids)
    if foreign:
        raise RuntimeError(f"AI_PROCESS_OWNER_UNGOVERNED_FACILITY_IDS:{','.join(foreign)}")
    packet["governance"] = {
        "owner": "SEMANTIC_AI_PROCESS_OWNER",
        "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
        "candidate_identity_closed_world": True,
        "unknown_is_not_default": True,
        "validated_facility_reference_count": len(referenced),
    }
    return packet


def attach_ai_process_owner(result: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    decision = result.setdefault("decision_intelligence", {})
    enabled = os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    required = os.getenv("OPTIME_AI_PROCESS_OWNER_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        decision["process_owner"] = {
            "owner": "SEMANTIC_AI_PROCESS_OWNER",
            "status": "REQUIRED_BUT_DISABLED" if required else "DISABLED",
            "phase": _phase(result),
        }
        if required:
            decision["recommendation_execution_allowed"] = False
        return result

    try:
        packet = _validate(_default_transport(_prompt(result, questionnaire_state, natural_language_query)), result)
        decision["process_owner"] = {"owner": "SEMANTIC_AI_PROCESS_OWNER", "status": "ACTIVE", **packet}
    except Exception as exc:
        decision["process_owner"] = {
            "owner": "SEMANTIC_AI_PROCESS_OWNER",
            "status": "FAILED",
            "phase": _phase(result),
            "error": str(exc),
        }
        if required:
            decision["recommendation_execution_allowed"] = False
    return result


__all__ = ["attach_ai_process_owner"]
