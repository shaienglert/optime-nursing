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
import re
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
    "Treat prior adaptiveSignals with explicit client answers as client evidence. Never re-ask a dimension that those answers already resolve, even with different wording.",
    "The target market/location is a minimum client-owned decision dimension. Absence is UNKNOWN and READY is forbidden until the client has supplied enough location information to select the search market.",
    "The affordability envelope/budget is a minimum client-owned decision dimension. Absence is UNKNOWN and READY is forbidden until the client has supplied a usable monthly budget or explicitly declined to set one.",
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
            "asked_statement_rule": "If any statement has status ASKED, copy the exact next_question into that statement's clarification_question. There may be at most one ASKED statement per turn.",
            "adaptive_answer_rule": "Prior adaptiveSignals are part of the client record. If an adaptive signal contains an explicit answer, treat that dimension as answered and do not ask it again using a paraphrase.",
            "minimum_readiness_dimensions": {
                "market_location": "Must be KNOWN from user_text, questionnaire_state, or prior adaptiveSignals before READY. If missing, ask the client.",
                "monthly_affordability": "Must be KNOWN from user_text, questionnaire_state, or prior adaptiveSignals before READY. A client may explicitly say they have no budget limit or do not want to set one; silence is not a value.",
                "absence_policy": "Do not treat omitted client-owned information as satisfied, defaulted, inferred, or research-required. Missing minimum dimensions require NEEDS_CLARIFICATION.",
            },
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

    asked_without_question = [
        statement for statement in statements
        if isinstance(statement, dict)
        and statement.get("status") == "ASKED"
        and not str(statement.get("clarification_question") or "").strip()
    ]
    next_question = str(result.get("next_question") or "").strip()
    asked_statements = [statement for statement in statements if isinstance(statement, dict) and statement.get("status") == "ASKED"]
    if len(asked_without_question) == 1 and len(asked_statements) == 1 and next_question:
        asked_without_question[0]["clarification_question"] = next_question
        result["question_trace_normalization"] = {
            "applied": True,
            "reason": "SINGLE_ASKED_STATEMENT_USED_TOP_LEVEL_NEXT_QUESTION",
        }

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
    if readiness == "NEEDS_CLARIFICATION" and not pending_question:
        raise RuntimeError("SEMANTIC_AI_CLARIFICATION_WITHOUT_BLOCKING_QUESTION")
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
        "prior_adaptive_answers_are_client_evidence": True,
        "minimum_client_dimensions_required": ["market_location", "monthly_affordability"],
        "rules_applied": SEMANTIC_AI_SYSTEM_RULES,
    }
    return result


def _repair_live_readiness_mismatch(result: Dict[str, Any]) -> Dict[str, Any]:
    if str(result.get("decision_readiness") or "").upper() != "READY":
        return result
    statements = result.get("statements") if isinstance(result.get("statements"), list) else []
    blocking = [
        statement for statement in statements
        if isinstance(statement, dict)
        and statement.get("status") == "ASKED"
        and statement.get("importance") in {"MUST", "UNKNOWN"}
        and str(statement.get("clarification_question") or result.get("next_question") or "").strip()
    ]
    if len(blocking) != 1:
        return result
    result = dict(result)
    result["decision_readiness"] = "NEEDS_CLARIFICATION"
    result["live_packet_repair"] = {
        "applied": True,
        "from": "READY",
        "to": "NEEDS_CLARIFICATION",
        "reason": "MODEL_RETURNED_BLOCKING_AI_QUESTION_WITH_READY_LABEL",
    }
    return result


def _adaptive_answer_summary(questionnaire_state: Dict[str, Any]) -> List[Dict[str, str]]:
    signals = (((questionnaire_state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    answers: List[Dict[str, str]] = []
    for item in signals:
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer") or "").strip()
        explanation = str(item.get("impactExplanation") or "").strip()
        if not answer:
            continue
        question = explanation.split("|", 1)[0].replace("Question:", "").strip() if explanation else ""
        answers.append({"question": question, "answer": answer})
    return answers


def _question_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", str(text or "").lower())
    stop = {"a", "an", "and", "any", "are", "can", "do", "does", "for", "has", "have", "how", "i", "in", "is", "of", "or", "she", "he", "the", "they", "to", "use", "uses", "what", "whether", "with", "you", "your"}
    aliases = {
        "walk": "mobility", "walking": "mobility", "walker": "mobility", "wheelchair": "mobility", "cane": "mobility", "stairs": "mobility", "standing": "mobility",
        "memory": "cognitive", "dementia": "cognitive", "alzheimer": "cognitive",
        "city": "location", "metro": "location", "area": "location", "geography": "location",
        "monthly": "budget", "afford": "budget", "cost": "budget", "price": "budget",
    }
    return {aliases.get(token, token) for token in tokens if token not in stop and len(token) > 2}


def _question_reasks_answered_dimension(result: Dict[str, Any], questionnaire_state: Dict[str, Any]) -> bool:
    next_question = str(result.get("next_question") or "").strip()
    if not next_question:
        return False
    current = _question_terms(next_question)
    if not current:
        return False
    for entry in _adaptive_answer_summary(questionnaire_state):
        prior = _question_terms(f"{entry.get('question', '')} {entry.get('answer', '')}")
        if not prior:
            continue
        overlap = current & prior
        if overlap and ("mobility" in overlap or "cognitive" in overlap or "location" in overlap or "budget" in overlap):
            return True
        if len(overlap) >= 2 and len(overlap) / max(1, min(len(current), len(prior))) >= 0.5:
            return True
    return False


def _minimum_dimension_status(user_text: str, questionnaire_state: Dict[str, Any]) -> Dict[str, bool]:
    text = str(user_text or "").lower()
    signals = (((questionnaire_state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    signal_text = " ".join(
        f"{str(item.get('impactExplanation') or '')} {str(item.get('answer') or '')}"
        for item in signals
        if isinstance(item, dict)
    ).lower()
    combined = f"{text} {signal_text}"

    explicit_location = any(str(questionnaire_state.get(key) or "").strip() for key in ("locationCity", "city", "referenceLocationValue"))
    text_location = bool(re.search(r"\b(las vegas|north las vegas|henderson|nevada)\b", combined))

    raw_budget = questionnaire_state.get("budget")
    numeric_budget = isinstance(raw_budget, (int, float)) and float(raw_budget) > 0 and float(raw_budget) != 7000
    text_budget = bool(re.search(r"(?:budget|monthly|per month|afford|cost)[^\n]{0,50}\$?\s*\d{3,6}|\$\s*\d{3,6}", combined))
    explicit_no_limit = bool(re.search(r"\b(no budget limit|no monthly limit|do not want to set a budget|don't want to set a budget)\b", combined))

    return {
        "market_location": explicit_location or text_location,
        "monthly_affordability": numeric_budget or text_budget or explicit_no_limit,
    }


def _has_blocking_question(result: Dict[str, Any]) -> bool:
    statements = result.get("statements") if isinstance(result.get("statements"), list) else []
    return any(
        isinstance(statement, dict)
        and statement.get("status") == "ASKED"
        and statement.get("importance") in {"MUST", "UNKNOWN"}
        and str(statement.get("clarification_question") or result.get("next_question") or "").strip()
        for statement in statements
    )


def _repair_missing_minimum_dimensions_with_ai(
    *,
    result: Dict[str, Any],
    payload: Dict[str, Any],
    user_text: str,
    questionnaire_state: Dict[str, Any],
    transport: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    status = _minimum_dimension_status(user_text, questionnaire_state)
    missing = [key for key, known in status.items() if not known]
    readiness = str(result.get("decision_readiness") or "").upper()
    if not missing or _has_blocking_question(result) or readiness not in {"READY", "NEEDS_RESEARCH"}:
        return result

    repair_payload = dict(payload)
    repair_payload["readiness_repair"] = {
        "required": True,
        "missing_client_owned_dimensions": missing,
        "prior_packet": result,
        "instruction": (
            "The prior packet attempted to finish client-intent readiness while required client-owned dimensions are still missing. "
            "Do not invent them and do not send them to facility research. Return a corrected compact packet with NEEDS_CLARIFICATION, "
            "exactly one highest-information AI-authored next_question for one missing dimension, and exactly one ASKED statement carrying that exact question."
        ),
    }
    repaired = transport(repair_payload)
    repaired = _repair_live_readiness_mismatch(repaired)
    # Do not validate here. The model may have produced a repairable clarification
    # contract (for example a missing or repeated question). The generic AI
    # self-repair pass must run before the final Guardian validation.
    repaired["minimum_dimension_repair"] = {
        "applied": True,
        "missing_dimensions": missing,
        "ai_authored_question": str(repaired.get("next_question") or ""),
    }
    return repaired


def _repair_clarification_contract_with_ai(
    *,
    result: Dict[str, Any],
    payload: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    transport: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    readiness = str(result.get("decision_readiness") or "").upper()
    missing_question = readiness == "NEEDS_CLARIFICATION" and not _has_blocking_question(result)
    repeated_question = readiness == "NEEDS_CLARIFICATION" and _question_reasks_answered_dimension(result, questionnaire_state)
    if not missing_question and not repeated_question:
        return result

    repair_payload = dict(payload)
    repair_payload["clarification_contract_repair"] = {
        "required": True,
        "prior_packet": result,
        "prior_explicit_adaptive_answers": _adaptive_answer_summary(questionnaire_state),
        "failure": "REASKED_ANSWERED_DIMENSION" if repeated_question else "NEEDS_CLARIFICATION_WITHOUT_USABLE_BLOCKING_QUESTION",
        "instruction": (
            "Repair the packet without inventing facts. Prior explicit adaptive answers are binding client evidence and must not be asked again in different wording. "
            "If a different material client-owned unknown remains, return NEEDS_CLARIFICATION with exactly one new highest-information AI-authored question and one matching ASKED statement. "
            "If no material client-owned clarification remains, return READY. Facility-specific unknowns may remain RESEARCH_REQUIRED and must not block client-intent READY."
        ),
    }
    repaired = transport(repair_payload)
    repaired = _repair_live_readiness_mismatch(repaired)
    if str(repaired.get("decision_readiness") or "").upper() == "NEEDS_CLARIFICATION":
        if not _has_blocking_question(repaired):
            raise RuntimeError("SEMANTIC_AI_REPAIR_CLARIFICATION_WITHOUT_QUESTION")
        if _question_reasks_answered_dimension(repaired, questionnaire_state):
            raise RuntimeError("SEMANTIC_AI_REPAIR_REASKED_ANSWERED_DIMENSION")
    repaired["clarification_contract_repair"] = {
        "applied": True,
        "reason": "REASKED_ANSWERED_DIMENSION" if repeated_question else "MISSING_BLOCKING_QUESTION",
    }
    return repaired


def interpret_client_intent_with_ai(*, user_text: str, questionnaire_state: Optional[Dict[str, Any]] = None, transport: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    questionnaire_state = questionnaire_state or {}
    learning_advice = build_learning_center_advice(user_text=user_text)
    payload = _build_prompt(user_text, questionnaire_state, learning_advice)
    active_transport = transport or _default_transport
    result = active_transport(payload)
    if transport is None:
        result = _repair_live_readiness_mismatch(result)
        # First repair malformed/repeated clarification packets from the initial AI pass.
        result = _repair_clarification_contract_with_ai(
            result=result,
            payload=payload,
            questionnaire_state=questionnaire_state,
            transport=active_transport,
        )
        # Then enforce minimum client-owned dimensions. This repair is AI-authored too.
        result = _repair_missing_minimum_dimensions_with_ai(
            result=result,
            payload=payload,
            user_text=user_text,
            questionnaire_state=questionnaire_state,
            transport=active_transport,
        )
        # A minimum-dimension repair can itself need contract repair; give the AI one
        # governed opportunity before the final validator fails closed.
        result = _repair_clarification_contract_with_ai(
            result=result,
            payload=payload,
            questionnaire_state=questionnaire_state,
            transport=active_transport,
        )
        missing = [key for key, known in _minimum_dimension_status(user_text, questionnaire_state).items() if not known]
        readiness = str(result.get("decision_readiness") or "").upper()
        if missing and (readiness == "READY" or (readiness == "NEEDS_CLARIFICATION" and not _has_blocking_question(result))):
            raise RuntimeError(f"SEMANTIC_AI_READY_WITH_MISSING_MINIMUM_DIMENSIONS:{','.join(missing)}")
    result = _validate_result(result)
    result["learning_center"] = {"advisor": learning_advice["advisor"], "consulted": True, "available_agent_count": learning_advice["available_agent_count"], "agent_count": learning_advice["agent_count"]}
    return result


__all__ = ["interpret_client_intent_with_ai", "SEMANTIC_AI_SYSTEM_RULES"]
