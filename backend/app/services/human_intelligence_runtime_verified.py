from __future__ import annotations

"""Verified adapter for Human Intelligence person-fit evidence.

The deterministic layer remains the guardrail. Semantic AI owns interview sequencing:
rules expose signals, constraints, and UNKNOWN states, but do not ask hard-coded
questions. The AI consults the OPTIME Nursing Learning Center and chooses the next
highest-information question until it returns READY. AI output remains governed and
cannot invent facility facts or silently resolve UNKNOWN values.
"""

import base64
import gzip
import hashlib
import json
import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, List

from app.services import human_intelligence_runtime as _base
from app.services.canonical_gap_policy import assess_gaps
from app.services.client_statement_accounting import account_user_input
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.semantic_intent_ai import interpret_client_intent_with_ai

has_explicit_person_fit_preference = _base.has_explicit_person_fit_preference
person_fit_sort_key = _base.person_fit_sort_key


def _semantic_question_key(question: str) -> str:
    normalized = " ".join(str(question or "").strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"semantic_ai_high_information_question:{digest}"


def _adaptive_signals(questionnaire_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    scoring = hi.get("scoringEngine") if isinstance(hi.get("scoringEngine"), dict) else {}
    signals = scoring.get("adaptiveSignals") if isinstance(scoring.get("adaptiveSignals"), list) else []
    return [row for row in signals if isinstance(row, dict)]


def _answered_adaptive_keys(questionnaire_state: Dict[str, Any]) -> set[str]:
    return {
        str(row.get("questionKey") or "")
        for row in _adaptive_signals(questionnaire_state)
        if str(row.get("questionKey") or "").strip()
    }


def _answered_fact_keys(questionnaire_state: Dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for row in _adaptive_signals(questionnaire_state):
        answer = str(row.get("answer") or "").strip()
        if not answer:
            continue
        fact_key = str(row.get("targetFactKey") or row.get("target_fact_key") or "").strip()
        if not fact_key:
            explanation = str(row.get("impactExplanation") or "")
            match = re.search(r"Target fact:\s*([A-Za-z0-9_]+)", explanation)
            if match:
                fact_key = match.group(1)
        if fact_key:
            keys.add(fact_key)
    return keys


def _explicit_client_fact_keys(questionnaire_state: Dict[str, Any], natural_language_query: str) -> set[str]:
    """Return client facts supplied directly, before the AI chooses interview order.

    A Guardian may veto readiness only for a fact that is actually unknown.  In
    particular, a clear affordability statement in free text must have the same
    effect as the structured ``budget`` field; otherwise the system asks for an
    answer that it already received.
    """
    facts: set[str] = set()
    raw_budget = questionnaire_state.get("budget")
    if isinstance(raw_budget, (int, float)) and not isinstance(raw_budget, bool) and float(raw_budget) > 0:
        facts.add("monthly_budget")

    text = str(natural_language_query or "")
    amount = r"(?:\$\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars?)\b)"
    budget_language = r"(?:monthly\s+)?(?:housing(?:\s*(?:and|&)\s*care)?\s+)?(?:budget|affordability|afford|cost|price|(?:can\s+)?spend|(?:can\s+)?pay)"
    has_explicit_budget = re.search(rf"{budget_language}[^.\n]{{0,80}}?{amount}", text, flags=re.IGNORECASE)
    has_explicit_no_limit = re.search(
        r"\b(?:no\s+(?:monthly\s+)?budget\s+limit|no\s+limit\s+on\s+(?:the\s+)?budget|do\s+not\s+want\s+to\s+set\s+a\s+budget|don't\s+want\s+to\s+set\s+a\s+budget)\b",
        text,
        flags=re.IGNORECASE,
    )
    if has_explicit_budget or has_explicit_no_limit:
        facts.add("monthly_budget")
    return facts


def _question_exists(context: Dict[str, Any], key: str) -> bool:
    return any(str(row.get("question_key") or "") == key for row in context.get("adaptive_questions") or [])


def _base_client_blockers(base_context: Dict[str, Any], answered_fact_keys: set[str]) -> List[Dict[str, Any]]:
    unresolved: List[Dict[str, Any]] = []
    for row in base_context.get("adaptive_questions") or []:
        if not isinstance(row, dict):
            continue
        fact_key = str(row.get("question_key") or "UNKNOWN")
        if fact_key in answered_fact_keys:
            continue
        information_gain = str(row.get("information_gain") or "").upper()
        if information_gain != "HIGH":
            continue
        unresolved.append({
            "fact_key": fact_key,
            "decision_dimensions": [str(value) for value in row.get("decision_dimensions") or []],
            "information_gain": information_gain,
            "reason": str(row.get("reason") or "Unresolved client fact can materially change the decision or transition plan."),
            "answer_options": [str(value) for value in row.get("answer_options") or []],
            "owner": "CLIENT",
            "source": "HUMAN_INTELLIGENCE_GUARDIAN",
        })
    return unresolved


def _strategy_client_blockers(strategy_context: Dict[str, Any], answered_fact_keys: set[str]) -> List[Dict[str, Any]]:
    unresolved: List[Dict[str, Any]] = []
    for row in strategy_context.get("guardian_clarification_candidates") or []:
        if not isinstance(row, dict):
            continue
        fact_key = str(row.get("question_key") or "UNKNOWN")
        if fact_key in answered_fact_keys:
            continue
        unresolved.append({
            "fact_key": fact_key,
            "decision_dimensions": ["living_strategy", fact_key],
            "information_gain": "HIGH",
            "reason": str(row.get("why_it_matters") or "Unresolved client fact can materially change the living-and-care strategy."),
            "answer_options": [str(value) for value in row.get("options") or []],
            # Open-ended facts (no closed options) carry their own approved question text.
            "fixed_question": str(row.get("question") or "") if not row.get("options") else "",
            "owner": "CLIENT",
            "source": "LIVING_STRATEGY_GUARDIAN",
        })
    return unresolved


def _governed_context(
    base_context: Dict[str, Any],
    strategy_context: Dict[str, Any],
    natural_language_query: str,
    questionnaire_state: Dict[str, Any],
) -> Dict[str, Any]:
    accounting = account_user_input(natural_language_query)
    # Facts count as answered only from the canonical state; text reaches it through the
    # interpreter's quoted patch, never through a regex here (single authority).
    answered_fact_keys = _answered_fact_keys(questionnaire_state) | _explicit_client_fact_keys(
        questionnaire_state,
        "",
    )
    blockers = _base_client_blockers(base_context, answered_fact_keys) + _strategy_client_blockers(strategy_context, answered_fact_keys)
    material_unknowns = [str(value) for value in strategy_context.get("material_unknowns") or []]
    sanitized_strategy_unknowns = [
        {
            "fact_key": item["fact_key"],
            "reason": item["reason"],
            "answer_options": item["answer_options"],
            "owner": item["owner"],
        }
        for item in blockers
        if item.get("source") == "LIVING_STRATEGY_GUARDIAN"
    ]
    return {
        "signals": base_context.get("signals") or {},
        "transition_support": base_context.get("transition_support") or {},
        "principles": base_context.get("principles") or [],
        "living_strategy_guardian": {
            "signals": strategy_context.get("signals") or {},
            "household": strategy_context.get("household") or {},
            "strategy_candidates": strategy_context.get("strategy_candidates") or [],
            "material_unknowns": material_unknowns,
            "client_owned_unknowns": sanitized_strategy_unknowns,
            "least_restrictive_safe_care_rule": bool(strategy_context.get("least_restrictive_safe_care_rule")),
            "policy": strategy_context.get("policy"),
            "rule": "Rules expose facts, constraints and unresolved dimensions only. They never supply user-facing question wording; Semantic AI owns the next question.",
        },
        "readiness_guardian": {
            "client_owned_blockers": blockers,
            "acknowledged_fact_keys": sorted(answered_fact_keys),
            "ready_veto_active": bool(blockers),
            "rule": "READY is forbidden while a material client-owned fact remains unresolved. Guardian identifies fact keys and decision impact; Semantic AI chooses wording and sequence. Explicit adaptive answers, including acknowledged unknowns, resolve the interview blocker without fabricating a value.",
        },
        "user_statement_accounting": accounting,
        "material_unknown_policy": {
            "unknown_is_not_default": True,
            "no_silent_drop": True,
            "required_statement_coverage_percent": 100,
            "rule": "CLIENT_OWNED_UNKNOWN=>ASK; PROVIDER_OWNED_UNKNOWN=>RESEARCH; MUST_FAIL=>BLOCK; UNKNOWN_NEVER_BECOMES_DEFAULT",
        },
        "interview_policy": {
            "owner": "SEMANTIC_AI",
            "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
            "one_high_information_question_at_a_time": True,
            "hard_coded_question_generation_forbidden": True,
            "ready_requires_ai_and_guardian": True,
            "strategy_rules_may_flag_unknowns_but_may_not_directly_ask": True,
        },
    }


def _call_semantic_ai(
    context: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    *,
    readiness_veto: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ai_state = dict(questionnaire_state)
    guardian_context = {
        "signals": context.get("signals") or {},
        "transition_support": context.get("transition_support") or {},
        "principles": context.get("principles") or [],
        "living_strategy_guardian": context.get("living_strategy_guardian") or {},
        "readiness_guardian": context.get("readiness_guardian") or {},
        "user_statement_accounting": context.get("user_statement_accounting") or {},
        "material_unknown_policy": context.get("material_unknown_policy") or {},
        "interview_policy": context.get("interview_policy") or {},
    }
    if readiness_veto:
        guardian_context["readiness_veto"] = readiness_veto
    ai_state["__optime_guardian_context"] = guardian_context
    return interpret_client_intent_with_ai(
        user_text=natural_language_query,
        questionnaire_state=ai_state,
    )


def _question_matches_guardian_target(result: Dict[str, Any], target: Dict[str, Any]) -> bool:
    """Reject an AI question whose declared semantic target differs from its UI target.

    The AI owns the wording, but a Guardian-selected answer set may only be attached
    to a question that resolves that same fact. Empty statement traces are retained
    for backwards-compatible test doubles and cannot establish a contradiction.
    """
    statements = result.get("statements")
    next_question = str(result.get("next_question") or "").strip()
    if not next_question:
        return True
    target_key = str(target.get("fact_key") or "").strip()
    text_patterns = {
        "monthly_budget": r"\b(?:budget|monthly cost|afford|spend)\b",
        "medicare_status": r"\b(?:medicare|insurance coverage)\b",
        "market_location": r"\b(?:city|location|area|market|las vegas|henderson)\b",
        "rehab_level_needed": r"\b(?:rehab|rehabilitation|pt|ot|speech therapy|personal care)\b",
        "move_timing_vs_rehab": r"\b(?:move timing|when .*move|hospital|currently in rehab)\b",
    }
    wording_pattern = text_patterns.get(target_key)
    wording_matches = bool(wording_pattern and re.search(wording_pattern, next_question.lower()))
    if not isinstance(statements, list) or not statements:
        return wording_matches
    asked = [row for row in statements if isinstance(row, dict) and str(row.get("status") or "").upper() == "ASKED"]
    if len(asked) != 1:
        return False
    asked_row = asked[0]
    declared = str(result.get("selected_fact_key") or asked_row.get("target_fact_key") or "").strip()
    mapped = {str(value).strip() for value in asked_row.get("mapped_parameters") or [] if str(value).strip()}
    semantic_aliases = {
        "monthly_budget": {"monthly_affordability", "budget"},
    }
    allowed_mappings = {target_key, *semantic_aliases.get(target_key, set())}
    return bool(target_key) and (declared == target_key or bool(mapped & allowed_mappings) or wording_matches)


def _canonical_fallback_result(base_result: Dict[str, Any], blocker: Dict[str, Any]) -> Dict[str, Any]:
    """Create neutral wording from the policy-owned gap contract."""
    fact_key = str(blocker.get("fact_key") or "required_information")
    options = [str(value) for value in blocker.get("answer_options") or []]
    readable_fact = fact_key.replace("_", " ")
    fallback_question = str(blocker.get("fixed_question") or "") or f"Which option best describes {readable_fact}: {', '.join(options)}?"
    return {
        **base_result,
        "decision_readiness": "NEEDS_CLARIFICATION",
        "next_question": fallback_question,
        "selected_fact_key": fact_key,
        # Keep the interpreter's own statements: they carry the exact family quotes that
        # every AI_EXTRACTED profile field needs. Dropping them used to leave the patch
        # in place without its quotes. The policy question is appended, not substituted.
        "statements": [*[s for s in base_result.get("statements") or [] if isinstance(s, dict) and str(s.get("status") or "").upper() != "ASKED"], {
            "raw_text": str(blocker.get("reason") or readable_fact),
            "meaning": str(blocker.get("reason") or readable_fact),
            "importance": "MUST",
            "knowledge_state": "UNKNOWN",
            "status": "ASKED",
            "gap_key": fact_key,
            "mapped_parameters": [fact_key],
            "clarification_question": fallback_question,
            "research_task": None,
        }],
    }


def _apply_canonical_policy_without_ai(
    context: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str
) -> Dict[str, Any]:
    """Preserve policy authority when semantic extraction/wording is unavailable."""
    guardian_gaps = list(((context.get("readiness_guardian") or {}).get("client_owned_blockers") or []))
    gap_policy = assess_gaps(
        guardian_gaps=guardian_gaps,
        ai_result={},
        questionnaire_state=questionnaire_state,
        user_text=natural_language_query,
    )
    blocking_keys = set(gap_policy.get("blocking_gap_keys") or [])
    blockers = [row for row in guardian_gaps if str(row.get("fact_key") or "") in blocking_keys]
    context["canonical_gap_policy"] = gap_policy
    context["readiness_guardian"]["client_owned_blockers"] = blockers
    context["readiness_guardian"]["ready_veto_active"] = bool(blockers) or bool(gap_policy.get("escalation_required"))
    context["adaptive_questions"] = []
    if blockers and (blockers[0].get("answer_options") or blockers[0].get("fixed_question")):
        blocker = blockers[0]
        fallback = _canonical_fallback_result({}, blocker)
        question_text = str(fallback["next_question"])
        question = _base._question(
            _semantic_question_key(question_text),
            question_text,
            "Canonical policy selected the highest-priority unresolved client fact while semantic wording was unavailable.",
            [str(value) for value in blocker.get("decision_dimensions") or ["client_intent_completeness"]],
            [str(value) for value in blocker.get("answer_options") or []],
        )
        question["target_fact_key"] = str(blocker.get("fact_key") or "required_information")
        question["question_owner"] = "DETERMINISTIC_CANONICAL_FALLBACK"
        context["adaptive_questions"] = [question]
        context["decision_readiness"] = "NEEDS_CLARIFICATION"
        context["readiness_guardian"]["selected_fact_key"] = question["target_fact_key"]
        context["readiness_guardian"]["fallback_reason"] = "SEMANTIC_AI_UNAVAILABLE"
    elif gap_policy.get("escalation_required"):
        context["decision_readiness"] = "NEEDS_CLARIFICATION"
    elif blockers:
        context["decision_readiness"] = "NEEDS_RESEARCH"
    else:
        context["decision_readiness"] = "READY"
    return context


def _consult_semantic_ai(
    context: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str, *,
    initial_result: Dict[str, Any] | None = None, initial_error: Exception | None = None,
) -> Dict[str, Any]:
    enabled = os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    required = os.getenv("OPTIME_SEMANTIC_AI_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    context["semantic_ai"] = {"enabled": enabled, "required": required, "status": "DISABLED"}

    if not enabled:
        if required:
            context["semantic_ai"]["status"] = "REQUIRED_BUT_DISABLED"
        return _apply_canonical_policy_without_ai(context, questionnaire_state, natural_language_query)

    try:
        # The interpreter already ran once (extraction pass); reuse its packet. Later calls
        # in this function are wording-only repairs for a target the policy selected.
        if initial_error is not None:
            raise initial_error
        result = initial_result if initial_result is not None else _call_semantic_ai(context, questionnaire_state, natural_language_query)
        readiness = str(result.get("decision_readiness") or "NEEDS_CLARIFICATION").upper()

        all_guardian_gaps = list(((context.get("readiness_guardian") or {}).get("client_owned_blockers") or []))
        gap_policy = assess_gaps(
            guardian_gaps=all_guardian_gaps,
            ai_result=result,
            questionnaire_state=questionnaire_state,
            user_text=natural_language_query,
        )
        blocking_keys = set(gap_policy.get("blocking_gap_keys") or [])
        blockers = [row for row in all_guardian_gaps if str(row.get("fact_key") or "") in blocking_keys]
        guardian_veto = readiness == "READY" and bool(blockers)
        selected_blocker: Dict[str, Any] | None = None
        # Only attach/validate a fixed target when Guardian supplied an answer
        # contract. Other semantic clarifications remain AI-owned free-form questions.
        declared_fact_key = str(result.get("selected_fact_key") or "").strip()
        has_semantic_trace = isinstance(result.get("statements"), list) and bool(result.get("statements"))
        question_matches_blocker = (
            _question_matches_guardian_target(result, blockers[0]) and bool(declared_fact_key or has_semantic_trace)
        ) if blockers else True
        # A model-authored question may never displace the deterministic blocker.
        # Wording remains AI-owned, but its declared semantic target must match
        # the canonical gap from the first turn; there is no free unstructured
        # question before resolving a blocking client fact.
        needs_target_repair = not question_matches_blocker
        suppress_misaligned_question = False
        if readiness == "NEEDS_CLARIFICATION" and blockers and blockers[0].get("answer_options") and needs_target_repair:
            selected_blocker = blockers[0]
            repair_packet = {
                "reason": "AI_QUESTION_TARGET_DOES_NOT_MATCH_GUARDIAN_BLOCKER",
                "highest_priority_fact_key": selected_blocker.get("fact_key"),
                "allowed_answer_options": selected_blocker.get("answer_options") or [],
                "instruction": "Ask exactly one concise question that resolves highest_priority_fact_key. Its wording, selected_fact_key, mapped_parameters, and answer options must all describe that same fact. Do not ask a different fact with this fact's answer options.",
            }
            repaired = result
            repair_succeeded = False
            for attempt in range(1, 4):
                repaired = _call_semantic_ai(context, questionnaire_state, natural_language_query, readiness_veto=repair_packet)
                if str(repaired.get("decision_readiness") or "").upper() == "NEEDS_CLARIFICATION" and _question_matches_guardian_target(repaired, selected_blocker):
                    repair_succeeded = True
                    context["readiness_guardian"]["question_target_repair_attempts"] = attempt
                    break
            result = repaired
            context["readiness_guardian"]["question_target_repair_applied"] = True
            if repair_succeeded:
                readiness = "NEEDS_CLARIFICATION"
                context["readiness_guardian"]["selected_fact_key"] = selected_blocker.get("fact_key")
            else:
                fact_key = str(selected_blocker.get("fact_key") or "required_information")
                result = _canonical_fallback_result(repaired, selected_blocker)
                readiness = "NEEDS_CLARIFICATION"
                context["readiness_guardian"]["selected_fact_key"] = fact_key
                context["readiness_guardian"]["question_target_repair_resolution"] = "DETERMINISTIC_CANONICAL_FALLBACK"
        if guardian_veto:
            selected_blocker = blockers[0]
            veto_packet = {
                "reason": "AI_READY_REJECTED_MATERIAL_CLIENT_UNKNOWN",
                "unresolved": blockers,
                "highest_priority_fact_key": selected_blocker.get("fact_key"),
                "instruction": "Ask exactly one concise question that resolves the highest-priority client-owned fact key. Do not copy deterministic wording because none is supplied. Do not return READY until the fact is answered or explicitly acknowledged as unknown/not sure.",
            }
            second_result: Dict[str, Any] = {}
            veto_succeeded = False
            for attempt in range(1, 4):
                second_result = _call_semantic_ai(
                    context,
                    questionnaire_state,
                    natural_language_query,
                    readiness_veto=veto_packet,
                )
                if (
                    str(second_result.get("decision_readiness") or "").upper() == "NEEDS_CLARIFICATION"
                    and _question_matches_guardian_target(second_result, selected_blocker)
                ):
                    veto_succeeded = True
                    context["readiness_guardian"]["veto_wording_attempts"] = attempt
                    break
            if veto_succeeded:
                result = second_result
                readiness = "NEEDS_CLARIFICATION"
                context["readiness_guardian"]["veto_applied"] = True
                context["readiness_guardian"]["veto_resolution"] = "RETURNED_TO_SEMANTIC_AI_FOR_NEXT_BEST_QUESTION"
                context["readiness_guardian"]["selected_fact_key"] = selected_blocker.get("fact_key")
            else:
                result = _canonical_fallback_result(second_result, selected_blocker)
                readiness = "NEEDS_CLARIFICATION"
                context["readiness_guardian"]["veto_applied"] = True
                context["readiness_guardian"]["veto_resolution"] = "DETERMINISTIC_CANONICAL_FALLBACK"
                context["readiness_guardian"]["selected_fact_key"] = selected_blocker.get("fact_key")

        # Re-evaluate after any AI wording repair.  This deterministic policy is
        # the sole authority for blocking, final client readiness and escalation;
        # the model's decision_readiness is retained only inside its audit packet.
        gap_policy = assess_gaps(
            guardian_gaps=all_guardian_gaps,
            ai_result=result,
            questionnaire_state=questionnaire_state,
            user_text=natural_language_query,
        )
        blocking_keys = set(gap_policy.get("blocking_gap_keys") or [])
        # Deterministic policy owns WHETHER another client fact is required and WHICH
        # fact is next.  Semantic AI owns only the conversational wording for that
        # already-selected target.  A missing/misaligned AI question therefore cannot
        # change readiness or choose an unstructured target.
        canonical_blockers = [
            row for row in all_guardian_gaps
            if str(row.get("fact_key") or "") in blocking_keys
        ]
        selected_blocker = canonical_blockers[0] if canonical_blockers else None
        if gap_policy.get("escalation_required") or blocking_keys:
            readiness = "NEEDS_CLARIFICATION"
        else:
            readiness = "READY"
        if selected_blocker is not None:
            context["readiness_guardian"]["selected_fact_key"] = selected_blocker.get("fact_key")
        context["canonical_gap_policy"] = gap_policy
        context["readiness_guardian"]["client_owned_blockers"] = [
            row for row in all_guardian_gaps if str(row.get("fact_key") or "") in blocking_keys
        ]
        context["readiness_guardian"]["nonblocking_gaps"] = [
            row for row in gap_policy.get("assessments") or [] if row.get("classification") != "BLOCKING"
        ]
        context["readiness_guardian"]["ready_veto_active"] = bool(blocking_keys) or bool(gap_policy.get("escalation_required"))

        context["semantic_ai"] = {
            "enabled": True,
            "required": required,
            "status": "CONSULTED_AND_VALIDATED" if readiness != "NEEDS_RESEARCH" else ("GUARDIAN_BLOCKED_READY" if guardian_veto else "CONSULTED_AND_VALIDATED"),
            "result": result,
        }
        context["decision_readiness"] = readiness
        context["adaptive_questions"] = []

        next_question = "" if suppress_misaligned_question else str(result.get("next_question") or "").strip()
        # The model's wording is accepted only when it addresses the deterministic
        # target. Otherwise use neutral canonical wording for the same target.
        if readiness == "NEEDS_CLARIFICATION" and selected_blocker is not None and (
            not next_question or not _question_matches_guardian_target(result, selected_blocker)
        ):
            fallback = _canonical_fallback_result({}, selected_blocker)
            next_question = str(fallback.get("next_question") or "")
        if readiness == "NEEDS_CLARIFICATION" and next_question:
            question_key = _semantic_question_key(next_question)
            answered_keys = _answered_adaptive_keys(questionnaire_state)
            if question_key not in answered_keys and not _question_exists(context, question_key):
                target = selected_blocker or (blockers[0] if blockers else {})
                # Never attach one Guardian fact's answer choices to an AI question
                # about another fact. If the semantic trace addresses a different
                # dimension, preserve the AI question as unstructured; the remaining
                # Guardian blocker will be asked in a later turn.
                if target.get("answer_options") and not _question_matches_guardian_target(result, target):
                    target = {
                        "fact_key": "semantic_ai_unstructured_fact",
                        "decision_dimensions": ["client_intent_completeness"],
                        "answer_options": [],
                    }
                question = _base._question(
                    question_key,
                    next_question,
                    "Governed Semantic AI selected this as the highest-information unresolved issue after consulting the Learning Center and Guardian context.",
                    [str(value) for value in target.get("decision_dimensions") or ["client_intent_completeness"]],
                    [str(value) for value in target.get("answer_options") or []],
                )
                question["target_fact_key"] = str(target.get("fact_key") or "semantic_ai_unstructured_fact")
                question["question_owner"] = "SEMANTIC_AI"
                context["adaptive_questions"] = [question]
        elif readiness in {"READY", "NEEDS_RESEARCH"}:
            context["adaptive_questions"] = []
    except Exception as exc:
        # Log only a bounded error category, never client text or provider bodies.
        error_code = str(exc).split(":", 1)[0]
        if not re.fullmatch(r"SEMANTIC_AI_[A-Z0-9_]{1,100}", error_code):
            error_code = type(exc).__name__
        logging.getLogger(__name__).warning("semantic_intake_failed code=%s", error_code)
        context["semantic_ai"] = {
            "enabled": True,
            "required": required,
            "status": "FAILED",
            "error": str(exc),
        }
        _apply_canonical_policy_without_ai(context, questionnaire_state, natural_language_query)
    return context


def build_human_intelligence_context(
    questionnaire_state: Dict[str, Any], natural_language_query: str = "", *,
    prepared_strategy: Dict[str, Any] | None = None,
    structured_only: bool = False,
) -> Dict[str, Any]:
    """One pass, in authority order (owner, 2026-10-02):

    1. Interpreter: the AI reads the family text once and returns a quoted patch.
    2. Canonical Structured Profile: buttons + validated patch -> materialized questionnaire.
    3. Strategy and Guardian, ONCE, from that canonical questionnaire only.
    4. Readiness and the next question from the deterministic gap policy; the AI may only
       word a target the policy selected.

    Nothing after step 2 reads the family text for facts. The text is used only for
    statement accounting and the deterministic immediate-safety screen.
    """
    from app.services.canonical_intake_state import canonicalize_intake_state
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

    enabled = not structured_only and os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    has_narrative = bool(str(natural_language_query or "").strip())

    # 1. Interpreter (extraction). It is given the interview policy, not a guardian built
    #    from pre-interpretation state: choosing the target is the policy's job (step 4).
    interpreter_result: Dict[str, Any] | None = None
    interpreter_error: Exception | None = None
    if enabled:
        try:
            interpreter_result = _call_semantic_ai(_interpreter_context(), questionnaire_state, natural_language_query)
        except Exception as exc:  # handled by the policy path in step 4
            interpreter_error = exc
    semantic_unavailable = (not enabled) or interpreter_error is not None

    # 2. Canonical profile.
    semantic_result = dict(interpreter_result or {})
    unprocessed_narrative = has_narrative and semantic_unavailable
    if unprocessed_narrative:
        semantic_result["_unprocessed_narrative"] = str(natural_language_query or "")
    structured = build_structured_profile(questionnaire_state, semantic_result, family_text=str(natural_language_query or ""))
    canonical = materialize_questionnaire(structured)
    if isinstance(questionnaire_state.get("questionnaireCompletion"), dict):
        canonical["questionnaireCompletion"] = questionnaire_state["questionnaireCompletion"]
    canonical = canonicalize_intake_state(canonical)

    # 3. Strategy and Guardian once, from canonical state.
    strategy_context = prepared_strategy if prepared_strategy is not None else build_living_strategy_context(canonical, "")
    base_context = _base.build_human_intelligence_context(canonical, "")
    context = _governed_context(base_context, strategy_context, natural_language_query, canonical)
    context["adaptive_questions"] = []
    context["decision_readiness"] = "NEEDS_CLARIFICATION"

    # 4. Readiness and question.
    context = (_apply_canonical_policy_without_ai(context, canonical, "") if structured_only
               else _consult_semantic_ai(context, canonical, natural_language_query, initial_result=interpreter_result, initial_error=interpreter_error))
    completion = questionnaire_state.get("questionnaireCompletion") or {}
    structured_complete = completion.get("mandatoryComplete") is True and completion.get("conditionalFollowUpsComplete") is True
    narrative_extraction_required = has_narrative and not structured_complete
    resolution_status = (
        "UNAVAILABLE" if narrative_extraction_required and semantic_unavailable
        else "UNPROCESSED" if structured_complete and unprocessed_narrative
        else "ASSESSED"
    )
    if resolution_status == "UNAVAILABLE":
        # The family's only account was never interpreted: the interview is not complete,
        # whatever the guardian sees in the (empty) canonical state.
        context["decision_readiness"] = "NEEDS_CLARIFICATION"
    context["structured_profile_shadow"] = structured
    context["canonical_decision_questionnaire"] = canonical
    context["canonical_living_strategy"] = strategy_context
    context["intake_resolution"] = {
        "source": "STRUCTURED" if structured_complete else "NARRATIVE",
        "narrative_extraction_required": narrative_extraction_required,
        "unprocessed_narrative": unprocessed_narrative,
        "status": resolution_status,
    }
    return context


def _interpreter_context() -> Dict[str, Any]:
    return {
        "interview_policy": {
            "owner": "SEMANTIC_AI",
            "role": "EXTRACT_CLIENT_FACTS_INTO_THE_CANONICAL_PROFILE_WITH_EXACT_QUOTES",
            "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
        },
        "material_unknown_policy": {"unknown_is_not_default": True, "no_silent_drop": True},
    }


@lru_cache(maxsize=1)
def _verified_person_fit_index() -> Dict[str, Dict[str, Any]]:
    text = _base._PERSON_FIT_PATH.read_text(encoding="utf-8").strip()
    decoded = gzip.decompress(base64.b64decode(text, validate=True))
    actual_payload_sha = hashlib.sha256(decoded).hexdigest()
    if actual_payload_sha != _base._PERSON_FIT_PAYLOAD_SHA256:
        raise RuntimeError(f"Las Vegas person-fit canonical payload checksum mismatch: sha256={actual_payload_sha} expected={_base._PERSON_FIT_PAYLOAD_SHA256}")
    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or []
    if payload.get("record_count") != _base._PERSON_FIT_RECORD_COUNT or len(records) != _base._PERSON_FIT_RECORD_COUNT:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 367 source records")
    if payload.get("beds_known_count") != _base._PERSON_FIT_BEDS_KNOWN:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 313 known official bed counts")
    return {str(row.get("canonical_id") or ""): row for row in records if row.get("canonical_id")}


def attach_human_person_fit(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> None:
    index = _verified_person_fit_index()
    preference = str((((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")).upper()
    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "")
        evidence = index.get(canonical_id) or {}
        beds = evidence.get("total_bed_count")
        if not isinstance(beds, int):
            beds = None
        source = "Nevada HCQC / ALiS official detail" if beds is not None else "UNKNOWN"
        evidence_class = "REGULATORY_VERIFIED" if beds is not None else "UNKNOWN"
        if row.get("synthetic_pilot") is True:
            pilot_band = str(row.get("community_size") or "").strip().upper()
            pilot_capacity = row.get("licensed_capacity")
            if pilot_band in {"SMALL", "MEDIUM", "LARGE"}:
                beds = pilot_capacity if isinstance(pilot_capacity, int) else None
                band = {
                    "SMALL": "SMALL_COMMUNITY",
                    "MEDIUM": "MEDIUM_COMMUNITY",
                    "LARGE": "LARGE_COMMUNITY",
                }[pilot_band]
                source = "Governed synthetic pilot catalog"
                evidence_class = "SYNTHETIC_PILOT_VERIFIED"
            else:
                band = _base._community_size_band(beds)
        else:
            band = _base._community_size_band(beds)
        fit = _base._size_fit(preference, band)
        row["human_person_fit"] = {
            "community_size": {
                "official_bed_count": beds if beds is not None else "UNKNOWN",
                "community_size_band": band,
                "preference": preference,
                "fit_score": fit if fit is not None else "UNKNOWN",
                "source": source,
                "evidence_class": evidence_class,
                "policy_role": "EXPLICIT_PREFERENCE_CONGRUENCE_ONLY",
                "not_a_quality_factor": True,
            },
            "social_transition_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility social-climate/engagement outcome evidence is attached yet.",
            },
            "independence_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility autonomy/choice evidence is attached yet.",
            },
        }


__all__ = [
    "attach_human_person_fit",
    "build_human_intelligence_context",
    "has_explicit_person_fit_preference",
    "person_fit_sort_key",
]
