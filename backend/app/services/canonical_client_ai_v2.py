from __future__ import annotations

"""V2 canonical client interpretation owned by Semantic AI.

One call converts questionnaire/free-text/prior adaptive evidence into the sole
client-owned decision state. The same call maps requirements to the canonical OPTIME
parameter registry when the registry can represent them. Novel requirements remain
explicit semantic requirements for research; no downstream keyword mapper is allowed.
"""

from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


_ALLOWED_IMPORTANCE = {"MUST", "NICE", "CONTEXT"}
_ALLOWED_KNOWLEDGE = {"KNOWN", "UNKNOWN", "AMBIGUOUS", "CONFLICT"}
_ALLOWED_OWNER = {"CLIENT", "FACILITY", "SYSTEM"}
_ALLOWED_STRATEGY_STATUS = {"LEADING", "STRONG_OPTION", "VALID_OPTION", "ALTERNATIVE_CONDITIONAL", "NEEDS_CLARIFICATION"}


def _compact_parameter_registry(parameter_registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    for row in parameter_registry.get("records") or []:
        if not isinstance(row, dict) or not str(row.get("parameter_id") or "").strip():
            continue
        compact.append(
            {
                "parameter_id": str(row.get("parameter_id")),
                "family": str(row.get("family") or ""),
                "display_name": str(row.get("display_name") or ""),
                "consumer_description": str(row.get("consumer_description") or "")[:240],
                "applicable_scope": str(row.get("applicable_scope") or ""),
                "hard_filter_eligibility": bool(row.get("hard_filter_eligibility")),
                "ranking_eligibility": bool(row.get("ranking_eligibility")),
            }
        )
    return compact


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
                "evidence_parameter_ids": ["existing parameter_id when semantically applicable"],
                "semantic_evidence_needed": False,
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
                "requirement_id": "req:id",
                "capability_key": "string",
                "reason": "string",
                "owner": "FACILITY",
            }
        ],
        "decision_readiness": "READY|NEEDS_CLARIFICATION",
    }


def _prompt(questionnaire_state: Dict[str, Any], natural_language_query: str, parameter_registry: Dict[str, Any]) -> Dict[str, Any]:
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
            "For every requirement, map to evidence_parameter_ids only when an available_parameter_registry definition semantically represents that requirement. Never invent a parameter_id.",
            "If the registry cannot represent a requirement precisely, leave evidence_parameter_ids empty and set semantic_evidence_needed=true. This is not an error and must not drop the requirement.",
            "A broad registry parameter must not be used as proof of a narrower service level unless its definition entails the requested level.",
            "Do not invent facility facts, prices, availability, or provider capabilities.",
            "UNKNOWN remains UNKNOWN. CONFLICT remains CONFLICT until resolved.",
            "Return compact JSON only.",
        ],
        "questionnaire_state": questionnaire_state,
        "natural_language_query": natural_language_query,
        "available_parameter_registry": _compact_parameter_registry(parameter_registry),
        "required_output": _required_output(),
    }


def _validate(packet: Dict[str, Any], parameter_registry: Dict[str, Any]) -> Dict[str, Any]:
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

    known_parameter_ids = {
        str(row.get("parameter_id"))
        for row in parameter_registry.get("records") or []
        if isinstance(row, dict) and str(row.get("parameter_id") or "").strip()
    }
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
        parameter_ids = [str(value) for value in row.get("evidence_parameter_ids") or [] if str(value)]
        semantic_needed = bool(row.get("semantic_evidence_needed", not parameter_ids))
        if not rid or not capability or importance not in {"MUST", "NICE"}:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_REQUIREMENT:{index}")
        if knowledge not in _ALLOWED_KNOWLEDGE or owner not in {"CLIENT", "FACILITY"}:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_INVALID_REQUIREMENT_STATE:{rid}")
        if not sources or not sources.issubset(known_statement_ids):
            raise RuntimeError(f"CANONICAL_CLIENT_AI_UNGROUNDED_REQUIREMENT:{rid}")
        foreign_parameters = sorted(set(parameter_ids) - known_parameter_ids)
        if foreign_parameters:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_UNKNOWN_PARAMETER_ID:{rid}:{','.join(foreign_parameters)}")
        if not parameter_ids and not semantic_needed:
            raise RuntimeError(f"CANONICAL_CLIENT_AI_REQUIREMENT_WITHOUT_EVIDENCE_PATH:{rid}")
        row["evidence_parameter_ids"] = parameter_ids
        row["semantic_evidence_needed"] = semantic_needed
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
        "requirements_bound_to_parameter_registry_or_semantic_research": True,
        "parameter_registry_count": len(known_parameter_ids),
        "process_owner": "SEMANTIC_AI",
        "guardian_role": "VALIDATE_CONSTRAIN_BLOCK",
    }
    return packet


def build_canonical_client_ai_state(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    transport: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
    parameter_registry: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    transport = transport or _default_transport
    if parameter_registry is None:
        from app.services.facility_parameter_service import get_parameter_registry_payload

        parameter_registry = get_parameter_registry_payload()
    return _validate(transport(_prompt(questionnaire_state, natural_language_query, parameter_registry)), parameter_registry)


__all__ = ["build_canonical_client_ai_state"]
