from __future__ import annotations

"""V2 canonical client interpretation owned by Semantic AI.

One call converts questionnaire/free-text/prior adaptive evidence into the sole
client-owned decision state. Downstream strategy, MUST and NICE layers consume the
canonical output; they do not parse raw client text again.
"""

from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


_ALLOWED_IMPORTANCE = {"MUST", "NICE", "CONTEXT"}
_ALLOWED_KNOWLEDGE = {"KNOWN", "UNKNOWN", "AMBIGUOUS", "CONFLICT"}
_ALLOWED_OWNER = {"CLIENT", "FACILITY", "SYSTEM"}
_ALLOWED_STRATEGY_STATUS = {"LEADING", "STRONG_OPTION", "VALID_OPTION", "ALTERNATIVE_CONDITIONAL", "NEEDS_CLARIFICATION"}


def _required_output() -> Dict[str, Any]:
    return {
        "statement_accounting": [
            {
                "statement_id": "s1",
                "raw_text": "string",
                "semantic_meaning": "string",
                "importance": "MUST|NICE|CONTEXT",
                "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS|CONFLICT",
                "owner": "CLIENT|FACILITY|SYSTEM",
                "used_in_requirement_ids": ["req:id"],
                "used_in_strategy_ids": ["strategy:id"],
            }
        ],
        "canonical_facts": [
            {
                "fact_key": "string",
                "value": "string|number|boolean|UNKNOWN|CONFLICT",
                "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS|CONFLICT",
                "source_statement_ids": ["s1"],
            }
        ],
        "requirements": [
            {
                "requirement_id": "req:id",
                "importance": "MUST|NICE",
                "capability_key": "open canonical semantic capability key",
                "required_service_level": "string|UNKNOWN",
                "client_expression": "string",
                "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS|CONFLICT",
                "owner": "CLIENT|FACILITY",
                "source_statement_ids": ["s1"],
            }
        ],
        "strategy_candidates": [
            {
                "strategy_id": "string",
                "status": "LEADING|STRONG_OPTION|VALID_OPTION|ALTERNATIVE_CONDITIONAL|NEEDS_CLARIFICATION",
                "rank_hint": 1,
                "rationale": "string",
                "required_capability_keys": ["string"],
                "source_statement_ids": ["s1"],
            }
        ],
        "next_question": {
            "question": "string|null",
            "resolves_statement_ids": ["s1"],
            "reason": "string|null",
        },
        "research_requests": [
            {
                "capability_key": "string",
                "reason": "string",
                "owner": "FACILITY",
            }
        ],
        "decision_readiness": "READY|NEEDS_CLARIFICATION",
    }


def _prompt(questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_CANONICAL_AI_PROCESS_OWNER_V2",
        "mission": "Interpret the complete client record exactly once into the canonical decision state used by every downstream Nursing decision component.",
        "rules": [
            "Account for every meaningful client statement exactly once in statement_accounting.",
            "Questionnaire values, free text, and prior adaptive answers are all client evidence.",
            "Never re-ask a dimension already answered by any client evidence source.",
            "Separate client-owned unknowns from facility-owned unknowns.",
            "Only a material client-owned ambiguity may produce next_question.",
            "Facility-owned unknowns become research_requests and never reopen the client interview.",
            "Classify explicit non-negotiable needs as MUST and preferences as NICE; do not invent MUSTs.",
            "Derive the least-restrictive safe living strategy from the whole client state, not keywords.",
            "A recent bereavement is context/social-transition evidence, not proof that the deceased spouse is a current co-resident.",
            "Do not invent facility facts, prices, availability, or provider capabilities.",
            "UNKNOWN remains UNKNOWN. CONFLICT remains CONFLICT until resolved.",
            "Return compact JSON only.",
        ],
        "questionnaire_state": questionnaire_state,
        "natural_language_query": natural_language_query,
        "required_output": _required_output(),
    }


def _validate(packet: Dict[str, Any]) -> Dict[str, Any]:
    statements = packet.get("statement_accounting") if isinstance(packet.get("statement_accounting"), list) else []
    if not statements:
        raise RuntimeError("CANONICAL_CLIENT_AI_MISSING_STATEMENT_ACCOUNTING")

    statement_ids: List[str] = []
    for index, row in enumerate(statements):
        if not isinstance(row, dict):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_STATEMENT:{index}")
        sid = str(row.get("statement_id") or "").strip()
        raw = str(row.get("raw_text") or "").strip()
        if not sid or not raw:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_STATEMENT:{index}")
        if str(row.get("importance") or "").upper() not in _ALLOWED_IMPORTANCE:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_IMPORTANCE:{sid}")
        if str(row.get("knowledge_state") or "").upper() not in _ALLOWED_KNOWLEDGE:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_KNOWLEDGE:{sid}")
        if str(row.get("owner") or "").upper() not in _ALLOWED_OWNER:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_OWNER:{sid}")
        statement_ids.append(sid)
    if len(statement_ids) != len(set(statement_ids)):
        raise RuntimeError("CANONICAL_CLIENT_AI_DUPLICATE_STATEMENT_ID")
    known_statement_ids = set(statement_ids)

    requirements = packet.get("requirements") if isinstance(packet.get("requirements"), list) else []
    req_ids: List[str] = []
    for index, row in enumerate(requirements):
        if not isinstance(row, dict):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_REQUIREMENT:{index}")
        rid = str(row.get("requirement_id") or "").strip()
        capability = str(row.get("capability_key") or "").strip()
        importance = str(row.get("importance") or "").upper()
        knowledge = str(row.get("knowledge_state") or "").upper()
        owner = str(row.get("owner") or "").upper()
        sources = {str(value) for value in row.get("source_statement_ids") or []}
        if not rid or not capability or importance not in {"MUST", "NICE"}:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_REQUIREMENT:{index}")
        if knowledge not in _ALLOWED_KNOWLEDGE or owner not in {"CLIENT", "FACILITY"}:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_REQUIREMENT_STATE:{rid}")
        if not sources or not sources.issubset(known_statement_ids):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_UNGROUNDED_REQUIREMENT:{rid}")
        req_ids.append(rid)
    if len(req_ids) != len(set(req_ids)):
        raise RuntimeError("CANONICAL_CLIENT_AI_DUPLICATE_REQUIREMENT_ID")

    strategies = packet.get("strategy_candidates") if isinstance(packet.get("strategy_candidates"), list) else []
    strategy_ids: List[str] = []
    for index, row in enumerate(strategies):
        if not isinstance(row, dict):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_STRATEGY:{index}")
        sid = str(row.get("strategy_id") or "").strip()
        status = str(row.get("status") or "").upper()
        sources = {str(value) for value in row.get("source_statement_ids") or []}
        if not sid or status not in _ALLOWED_STRATEGY_STATUS:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_STRATEGY:{index}")
        if sources and not sources.issubset(known_statement_ids):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_UNGROUNDED_STRATEGY:{sid}")
        strategy_ids.append(sid)
    if len(strategy_ids) != len(set(strategy_ids)):
        raise RuntimeError("CANONICAL_CLIENT_AI_DUPLICATE_STRATEGY_ID")

    readiness = str(packet.get("decision_readiness") or "").upper()
    question = packet.get("next_question") if isinstance(packet.get("next_question"), dict) else {}
    question_text = str(question.get("question") or "").strip()
    resolves = {str(value) for value in question.get("resolves_statement_ids") or []}
    if readiness not in {"READY", "NEEDS_CLARIFICATION"}:
        raise RuntimeError("CANONICAL_CLIENT_AI_INVALID_READINESS")
    if readiness == "NEEDS_CLARIFICATION":
        if not question_text or not resolves or not resolves.issubset(known_statement_ids):
            raise RuntimeError("CANONICAL_CLIENT_AI_CLARIFICATION_WITHOUT_GROUNDED_QUESTION")
    elif question_text:
        raise RuntimeError("CANONICAL_CLIENT_AI_READY_WITH_QUESTION")

    packet["governance"] = {
        "single_interpretation": True,
        "statement_accounting_percent": 100.0,
        "downstream_raw_text_reparse_forbidden": True,
        "unknown_is_not_default": True,
        "process_owner": "SEMANTIC_AI",
        "guardian_role": "VALIDATE_CONSTRAIN_BLOCK",
    }
    return packet


def build_canonical_client_ai_state(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    transport: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    transport = transport or _default_transport
    return _validate(transport(_prompt(questionnaire_state, natural_language_query)))


__all__ = ["build_canonical_client_ai_state"]
