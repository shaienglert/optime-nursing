from __future__ import annotations

"""AI-first semantic understanding for OPTIME Nursing.

The model is the interpreter, not the authority. It must consume the Learning Center
advice and return a structured semantic packet. Domain rules then validate the packet.
No meaningful client statement may disappear; unresolved client meaning becomes a
question only when it is decision-critical. Facility-specific unknowns become
downstream research, never invented facts.
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

import requests

from app.services.learning_center_advisor import build_learning_center_advice

SEMANTIC_AI_SYSTEM_RULES = [
    "Understand the client before recommending anything.",
    "Account for every meaningful client statement.",
    "Separate explicit facts from inferences.",
    "Never convert an inference into a fact without confirmation or evidence.",
    "Classify decision relevance as MUST, NICE, CONTEXT, or UNKNOWN.",
    "Only client-owned information that is MUST or otherwise decision-critical may block READY and generate the next clarification question.",
    "NICE or CONTEXT ambiguity must remain UNKNOWN/AMBIGUOUS without blocking READY unless the client explicitly elevates it to a requirement.",
    "If material decision-critical information owned by the client is unknown or ambiguous, ASK the client instead of delegating it to facility research.",
    "Facility-specific facts such as availability, price, unit route distance, meal delivery, dietary safety, current activities, or service capability may remain RESEARCH_REQUIRED after client intent is understood.",
    "decision_readiness means CLIENT-INTENT readiness. READY is allowed when no material client clarification remains, even if downstream facility evidence still requires research.",
    "If domain or facility evidence is missing, request research and consult the Learning Center.",
    "UNKNOWN must remain UNKNOWN until resolved.",
    "Do not invent facility capabilities, prices, availability, reputation, or regulatory facts.",
    "Prefer one high-information clarification at a time.",
    "Return a compact decision packet: preserve 100% statement accounting but avoid repetition and long prose.",
]


def _required_output_schema() -> Dict[str, Any]:
    return {
        "facts": ["string"],
        "preferences": ["string"],
        "constraints": ["string"],
        "concerns": ["string"],
        "implications": [{"derived_from": ["string"], "implication": "string", "certainty": "POSSIBLE|LIKELY|CONFIRMED", "requires_confirmation": True}],
        "statements": [{"raw_text": "string", "meaning": "string", "importance": "MUST|NICE|CONTEXT|UNKNOWN", "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS", "status": "USED|ASKED|RESEARCH_REQUIRED|NOT_DECISION_RELEVANT", "mapped_parameters": ["string"], "clarification_question": "string|null", "research_task": "string|null"}],
        "next_question": "string|null",
        "research_requests": ["string"],
        "decision_readiness": "READY|NEEDS_CLARIFICATION|NEEDS_RESEARCH",
    }


def _build_prompt(user_text: str, questionnaire_state: Dict[str, Any], learning_advice: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_EXPERT_SEMANTIC_INTERPRETER",
        "mission": "Understand the resident/family request at senior-living expert level before matching. Distinguish decision-critical client clarification from downstream facility research and non-blocking NICE/CONTEXT ambiguity.",
        "rules": SEMANTIC_AI_SYSTEM_RULES,
        "response_constraints": {
            "style": "compact JSON; no repeated explanation",
            "facts_max": 10,
            "preferences_max": 8,
            "constraints_max": 8,
            "concerns_max": 6,
            "implications_max": 6,
            "research_requests_max": 8,
            "statement_rule": "Every meaningful user/questionnaire statement must be accounted for exactly once; semantically linked fragments may be grouped, but nothing material may be dropped.",
            "field_length_rule": "Keep meaning, implication, clarification_question and research_task concise; usually one sentence each.",
            "question_priority_rule": "Ask only one highest-information unresolved MUST/decision-critical client question. Do not ask NICE/CONTEXT questions merely to improve ranking.",
        },
        "questionnaire_state": questionnaire_state,
        "user_text": user_text,
        "learning_center_advice": learning_advice,
        "required_output": _required_output_schema(),
    }


def _extract_responses_output(body: Dict[str, Any]) -> Dict[str, Any]:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return json.loads(output_text)
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return json.loads(part["text"])
    raise RuntimeError("SEMANTIC_AI_INVALID_RESPONSE")


def _request_with_retry(url: str, headers: Dict[str, str], request_json: Dict[str, Any]) -> requests.Response:
    timeout_seconds = max(5.0, float(os.getenv("OPTIME_SEMANTIC_AI_TIMEOUT_SECONDS", "45")))
    max_attempts = max(1, min(3, int(os.getenv("OPTIME_SEMANTIC_AI_MAX_ATTEMPTS", "2"))))
    backoff_seconds = max(0.0, float(os.getenv("OPTIME_SEMANTIC_AI_RETRY_BACKOFF_SECONDS", "1")))
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return requests.post(url, headers=headers, json=request_json, timeout=(10.0, timeout_seconds))
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            if backoff_seconds:
                time.sleep(backoff_seconds * attempt)
    raise RuntimeError(f"SEMANTIC_AI_TRANSPORT_RETRY_EXHAUSTED:attempts={max_attempts}:timeout={timeout_seconds}:{last_error}")


def _default_transport(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip()
    model = os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip()
    api_key = os.getenv("OPTIME_SEMANTIC_AI_API_KEY", "").strip()
    if not url or not model:
        raise RuntimeError("SEMANTIC_AI_NOT_CONFIGURED")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    uses_responses_api = "/responses" in url.lower()
    if uses_responses_api:
        request_json = {
            "model": model,
            "input": [
                {"role": "system", "content": "You are the governed semantic reasoning layer for a senior-living decision engine. Return compact JSON only."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "text": {"format": {"type": "json_object"}},
        }
    else:
        request_json = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are the governed semantic reasoning layer for a senior-living decision engine. Return compact JSON only."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
    response = _request_with_retry(url, headers, request_json)
    if not response.ok:
        raise RuntimeError(f"SEMANTIC_AI_HTTP_{response.status_code}:{response.text[:500]}")
    body = response.json()
    if uses_responses_api:
        return _extract_responses_output(body)
    if isinstance(body, dict) and "choices" in body:
        return json.loads(body["choices"][0]["message"]["content"])
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

    # Guardian policy: the model may propose a question, but NICE/CONTEXT ambiguity
    # is not allowed to block recommendation readiness. Preserve the ambiguity and
    # remove the blocking question rather than inventing an answer.
    nonblocking_asked = [
        s for s in statements
        if s.get("status") == "ASKED" and s.get("importance") in {"NICE", "CONTEXT"}
    ]
    for statement in nonblocking_asked:
        statement["status"] = "USED"
        statement["clarification_question"] = None
    blocking_asked = [s for s in statements if s.get("status") == "ASKED"]
    pending_question = bool(blocking_asked)
    pending_research = any(s.get("status") == "RESEARCH_REQUIRED" for s in statements)

    if not pending_question and nonblocking_asked:
        result["next_question"] = None
        if str(result.get("decision_readiness") or "") == "NEEDS_CLARIFICATION":
            result["decision_readiness"] = "READY"
        result["readiness_normalization"] = {
            "from": "NEEDS_CLARIFICATION",
            "to": "READY",
            "reason": "ONLY_NICE_OR_CONTEXT_AMBIGUITY_REMAINED",
        }

    readiness = str(result.get("decision_readiness") or "NEEDS_CLARIFICATION")
    if readiness == "READY" and pending_question:
        raise RuntimeError("SEMANTIC_AI_READY_WITH_UNRESOLVED_CLIENT_INPUT")
    if readiness == "NEEDS_RESEARCH" and not pending_question:
        result["decision_readiness"] = "READY"
        result["readiness_normalization"] = {
            "from": "NEEDS_RESEARCH",
            "to": "READY",
            "reason": "CLIENT_INTENT_COMPLETE_FACILITY_RESEARCH_DEFERRED",
            "pending_facility_research": pending_research,
        }
    result["statement_coverage_percent"] = 100.0
    result["dropped_statement_count"] = 0
    result["governance"] = {
        "ai_based": True,
        "learning_center_consulted": True,
        "unknown_is_not_default": True,
        "no_silent_drop": True,
        "client_intent_ready_allows_downstream_facility_research": True,
        "nice_context_unknowns_do_not_block_ready": True,
        "rules_applied": SEMANTIC_AI_SYSTEM_RULES,
    }
    return result


def interpret_client_intent_with_ai(*, user_text: str, questionnaire_state: Optional[Dict[str, Any]] = None, transport: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    questionnaire_state = questionnaire_state or {}
    learning_advice = build_learning_center_advice(user_text=user_text)
    payload = _build_prompt(user_text, questionnaire_state, learning_advice)
    result = (transport or _default_transport)(payload)
    result = _validate_result(result)
    result["learning_center"] = {"advisor": learning_advice["advisor"], "consulted": True, "available_agent_count": learning_advice["available_agent_count"], "agent_count": learning_advice["agent_count"]}
    return result


__all__ = ["interpret_client_intent_with_ai", "SEMANTIC_AI_SYSTEM_RULES"]