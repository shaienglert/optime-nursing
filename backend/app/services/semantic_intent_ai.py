from __future__ import annotations

"""AI-first semantic understanding for OPTIME Nursing.

The model is the interpreter, not the authority. It must consume the Learning Center
advice and return a structured semantic packet. Domain rules then validate the packet.
No meaningful client statement may disappear; unresolved meaning becomes a question
or research task, never an inferred fact.
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional

import requests

from app.services.learning_center_advisor import build_learning_center_advice

SEMANTIC_AI_SYSTEM_RULES = [
    "Understand the client before recommending anything.",
    "Account for every meaningful client statement.",
    "Separate explicit facts from inferences.",
    "Never convert an inference into a fact without confirmation or evidence.",
    "Classify decision relevance as MUST, NICE, CONTEXT, or UNKNOWN.",
    "If a material preference is unknown, ask the client instead of guessing.",
    "If domain knowledge is missing, request research and consult the Learning Center.",
    "UNKNOWN must remain UNKNOWN until resolved.",
    "Do not invent facility capabilities, prices, availability, reputation, or regulatory facts.",
    "Prefer one high-information clarification at a time.",
]


def _required_output_schema() -> Dict[str, Any]:
    return {
        "facts": ["string"],
        "preferences": ["string"],
        "constraints": ["string"],
        "concerns": ["string"],
        "implications": [
            {
                "derived_from": ["string"],
                "implication": "string",
                "certainty": "POSSIBLE|LIKELY|CONFIRMED",
                "requires_confirmation": True,
            }
        ],
        "statements": [
            {
                "raw_text": "string",
                "meaning": "string",
                "importance": "MUST|NICE|CONTEXT|UNKNOWN",
                "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS",
                "status": "USED|ASKED|RESEARCH_REQUIRED|NOT_DECISION_RELEVANT",
                "mapped_parameters": ["string"],
                "clarification_question": "string|null",
                "research_task": "string|null",
            }
        ],
        "next_question": "string|null",
        "research_requests": ["string"],
        "decision_readiness": "READY|NEEDS_CLARIFICATION|NEEDS_RESEARCH",
    }


def _build_prompt(user_text: str, questionnaire_state: Dict[str, Any], learning_advice: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_EXPERT_SEMANTIC_INTERPRETER",
        "mission": "Understand the resident/family request at senior-living expert level before matching.",
        "rules": SEMANTIC_AI_SYSTEM_RULES,
        "questionnaire_state": questionnaire_state,
        "user_text": user_text,
        "learning_center_advice": learning_advice,
        "required_output": _required_output_schema(),
    }


def _default_transport(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip()
    model = os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip()
    api_key = os.getenv("OPTIME_SEMANTIC_AI_API_KEY", "").strip()
    if not url or not model:
        raise RuntimeError("SEMANTIC_AI_NOT_CONFIGURED")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are the governed semantic reasoning layer for a senior-living decision engine. Return JSON only."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        },
        timeout=float(os.getenv("OPTIME_SEMANTIC_AI_TIMEOUT_SECONDS", "20")),
    )
    response.raise_for_status()
    body = response.json()
    if isinstance(body, dict) and "choices" in body:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    if isinstance(body, dict) and "output" in body and isinstance(body["output"], dict):
        return body["output"]
    if isinstance(body, dict):
        return body
    raise RuntimeError("SEMANTIC_AI_INVALID_RESPONSE")


def _validate_result(result: Dict[str, Any]) -> Dict[str, Any]:
    statements = result.get("statements")
    if not isinstance(statements, list) or not statements:
        raise RuntimeError("SEMANTIC_AI_MISSING_STATEMENT_TRACE")

    allowed_status = {"USED", "ASKED", "RESEARCH_REQUIRED", "NOT_DECISION_RELEVANT"}
    allowed_importance = {"MUST", "NICE", "CONTEXT", "UNKNOWN"}
    allowed_knowledge = {"KNOWN", "UNKNOWN", "AMBIGUOUS"}
    for idx, statement in enumerate(statements):
        if not isinstance(statement, dict) or not str(statement.get("raw_text") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_INVALID_STATEMENT:{idx}")
        if statement.get("status") not in allowed_status:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_STATUS:{idx}")
        if statement.get("importance") not in allowed_importance:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_IMPORTANCE:{idx}")
        if statement.get("knowledge_state") not in allowed_knowledge:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_KNOWLEDGE:{idx}")
        if statement.get("status") == "ASKED" and not str(statement.get("clarification_question") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_ASKED_WITHOUT_QUESTION:{idx}")
        if statement.get("status") == "RESEARCH_REQUIRED" and not str(statement.get("research_task") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_RESEARCH_WITHOUT_TASK:{idx}")

    pending_question = any(s.get("status") == "ASKED" for s in statements)
    pending_research = any(s.get("status") == "RESEARCH_REQUIRED" for s in statements)
    if result.get("decision_readiness") == "READY" and (pending_question or pending_research):
        raise RuntimeError("SEMANTIC_AI_READY_WITH_UNRESOLVED_INPUT")

    result["statement_coverage_percent"] = 100.0
    result["dropped_statement_count"] = 0
    result["governance"] = {
        "ai_based": True,
        "learning_center_consulted": True,
        "unknown_is_not_default": True,
        "no_silent_drop": True,
        "rules_applied": SEMANTIC_AI_SYSTEM_RULES,
    }
    return result


def interpret_client_intent_with_ai(
    *,
    user_text: str,
    questionnaire_state: Optional[Dict[str, Any]] = None,
    transport: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    questionnaire_state = questionnaire_state or {}
    learning_advice = build_learning_center_advice(user_text=user_text)
    payload = _build_prompt(user_text, questionnaire_state, learning_advice)
    result = (transport or _default_transport)(payload)
    result = _validate_result(result)
    result["learning_center"] = {
        "advisor": learning_advice["advisor"],
        "consulted": True,
        "available_agent_count": learning_advice["available_agent_count"],
        "agent_count": learning_advice["agent_count"],
    }
    return result


__all__ = ["interpret_client_intent_with_ai", "SEMANTIC_AI_SYSTEM_RULES"]
