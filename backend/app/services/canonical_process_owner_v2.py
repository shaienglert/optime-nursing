from __future__ import annotations

"""Governed downstream synthesis for the V2 Semantic AI Process Owner.

The Process Owner explains the already-governed decision and chooses the next process
action. It cannot change canonical facts, MUST state, candidate membership or rank.
"""

from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


Transport = Callable[[Dict[str, Any]], Dict[str, Any]]
_ALLOWED_ACTIONS = {"PRESENT_RESULTS", "VERIFY_PROVIDER", "RESEARCH_PROVIDER", "FOLLOW_UP"}


def _result_packet(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "canonical_facility_id": row.get("canonical_facility_id"),
        "facility_name": row.get("facility_name"),
        "rank": (row.get("ai_ranking") or {}).get("rank"),
        "ai_ranking": row.get("ai_ranking") or {},
        "authoritative_must": row.get("authoritative_must") or {},
        "nice_verification": row.get("nice_verification") or {},
    }


def _prompt(decision: Dict[str, Any]) -> Dict[str, Any]:
    client_state = decision.get("canonical_client_state") if isinstance(decision.get("canonical_client_state"), dict) else {}
    return {
        "role": "OPTIME_NURSING_AI_PROCESS_OWNER_V2",
        "mission": "Explain the governed current decision to the client and select the next best process action. Preserve all authoritative facts, MUST decisions and AI ranks exactly.",
        "rules": [
            "Do not add, remove, reorder or rename facilities.",
            "Do not change any authoritative MUST status.",
            "Do not invent prices, availability, services, activities, quality, reputation or provider facts.",
            "If a NICE item is UNKNOWN, explain that it is unverified and may affect ordering after verification; do not call it absent.",
            "If pending MUST candidates exist outside the visible ranking, state that the current shortlist is provisional because those candidates may enter after verification.",
            "If fewer than five facilities passed every MUST, present the genuine number; never imply the system should fill five slots.",
            "Use concise senior-readable language. Avoid internal labels such as POTENTIALLY_ELIGIBLE, low confidence, CMS placeholder or raw enum names in client_message.",
            "Provider verification is a proposal for improving precision; never claim that outreach has occurred.",
        ],
        "decision_status": decision.get("status"),
        "candidate_counts": {
            "universe": decision.get("candidate_universe_count"),
            "must_eligible": decision.get("must_eligible_count"),
            "must_pending": decision.get("must_pending_verification_count"),
            "must_rejected": decision.get("must_rejected_count"),
        },
        "canonical_client_requirements": client_state.get("requirements") or [],
        "visible_results": [_result_packet(row) for row in decision.get("results") or []],
        "pending_verification": decision.get("pending_verification") or [],
        "required_output": {
            "phase": "COMPARE|VERIFY|FOLLOW_UP",
            "decision_finality": "CURRENT_VERIFIED_SHORTLIST|PROVISIONAL_PENDING_PROVIDER_VERIFICATION",
            "next_action": "PRESENT_RESULTS|VERIFY_PROVIDER|RESEARCH_PROVIDER|FOLLOW_UP",
            "client_message": "concise senior-readable summary",
            "why_these_results": ["concise reason"],
            "facts_to_verify": [
                {
                    "canonical_facility_id": "string",
                    "requirement_id": "string|null",
                    "question": "specific provider question",
                    "why_it_matters": "string",
                }
            ],
            "visible_candidate_ids_in_rank_order": ["canonical_facility_id"],
        },
    }


def _validate(packet: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    expected_ids = [str(row.get("canonical_facility_id")) for row in decision.get("results") or []]
    actual_ids = [str(value) for value in packet.get("visible_candidate_ids_in_rank_order") or []]
    if actual_ids != expected_ids:
        raise RuntimeError("V2_PROCESS_OWNER_CHANGED_VISIBLE_RANKING")

    action = str(packet.get("next_action") or "").upper()
    if action not in _ALLOWED_ACTIONS:
        raise RuntimeError(f"V2_PROCESS_OWNER_INVALID_ACTION:{action}")

    pending_count = int(decision.get("must_pending_verification_count") or 0)
    finality = str(packet.get("decision_finality") or "").upper()
    if pending_count > 0 and finality != "PROVISIONAL_PENDING_PROVIDER_VERIFICATION":
        raise RuntimeError("V2_PROCESS_OWNER_HID_PENDING_MUST_UNIVERSE")

    result_ids = set(expected_ids)
    pending_ids = {str(row.get("canonical_facility_id")) for row in decision.get("pending_verification") or []}
    valid_ids = result_ids | pending_ids
    facts = packet.get("facts_to_verify") if isinstance(packet.get("facts_to_verify"), list) else []
    for fact in facts:
        if not isinstance(fact, dict):
            raise RuntimeError("V2_PROCESS_OWNER_INVALID_VERIFICATION_FACT")
        cid = str(fact.get("canonical_facility_id") or "")
        if cid and cid not in valid_ids:
            raise RuntimeError(f"V2_PROCESS_OWNER_UNKNOWN_FACILITY:{cid}")
        if not str(fact.get("question") or "").strip():
            raise RuntimeError("V2_PROCESS_OWNER_EMPTY_PROVIDER_QUESTION")

    return {
        "owner": "SEMANTIC_AI",
        "version": "canonical-process-owner-v2",
        "phase": str(packet.get("phase") or "COMPARE").upper(),
        "decision_finality": finality or ("PROVISIONAL_PENDING_PROVIDER_VERIFICATION" if pending_count else "CURRENT_VERIFIED_SHORTLIST"),
        "next_action": action,
        "client_message": str(packet.get("client_message") or "").strip(),
        "why_these_results": [str(value) for value in packet.get("why_these_results") or []],
        "facts_to_verify": facts,
        "visible_candidate_ids_in_rank_order": actual_ids,
        "governance": {
            "may_change_must": False,
            "may_change_ranking": False,
            "may_invent_facility_facts": False,
            "may_choose_next_process_action": True,
        },
    }


def synthesize_process_owner_v2(
    decision: Dict[str, Any],
    *,
    transport: Transport = _default_transport,
) -> Dict[str, Any]:
    return _validate(transport(_prompt(decision)), decision)


__all__ = ["synthesize_process_owner_v2"]
