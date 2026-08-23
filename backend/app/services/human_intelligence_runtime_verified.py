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
import os
from functools import lru_cache
from typing import Any, Dict, List

from app.services import human_intelligence_runtime as _base
from app.services.client_statement_accounting import account_user_input
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.semantic_intent_ai import interpret_client_intent_with_ai

has_explicit_person_fit_preference = _base.has_explicit_person_fit_preference
person_fit_sort_key = _base.person_fit_sort_key


def _semantic_question_key(question: str) -> str:
    normalized = " ".join(str(question or "").strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"semantic_ai_high_information_question:{digest}"


def _answered_adaptive_keys(questionnaire_state: Dict[str, Any]) -> set[str]:
    hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    scoring = hi.get("scoringEngine") if isinstance(hi.get("scoringEngine"), dict) else {}
    signals = scoring.get("adaptiveSignals") if isinstance(scoring.get("adaptiveSignals"), list) else []
    return {
        str(row.get("questionKey") or "")
        for row in signals
        if isinstance(row, dict) and str(row.get("questionKey") or "").strip()
    }


def _question_exists(context: Dict[str, Any], key: str) -> bool:
    return any(str(row.get("question_key") or "") == key for row in context.get("adaptive_questions") or [])


def _rank_sensitive_unknowns(base_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return only deterministic evidence that an unresolved answer can change ordering.

    Rules are allowed to identify the unresolved decision dimension, but never to choose
    or emit the user-facing question. Semantic AI remains responsible for wording and
    sequencing. This Guardian list exists only to veto a premature READY.
    """
    unresolved: List[Dict[str, Any]] = []
    for row in base_context.get("adaptive_questions") or []:
        if not isinstance(row, dict):
            continue
        dimensions = [str(value) for value in row.get("decision_dimensions") or []]
        information_gain = str(row.get("information_gain") or "").upper()
        if information_gain != "HIGH" or "preference_congruence" not in dimensions:
            continue
        unresolved.append({
            "question_key": str(row.get("question_key") or "UNKNOWN"),
            "decision_dimensions": dimensions,
            "information_gain": information_gain,
            "reason": str(row.get("reason") or "Unresolved preference can materially change candidate ordering."),
        })
    return unresolved


def _governed_context(
    base_context: Dict[str, Any],
    strategy_context: Dict[str, Any],
    natural_language_query: str,
) -> Dict[str, Any]:
    """Convert deterministic runtime output into Guardian evidence, never interview control."""
    accounting = account_user_input(natural_language_query)
    rank_sensitive_unknowns = _rank_sensitive_unknowns(base_context)
    return {
        "signals": base_context.get("signals") or {},
        "transition_support": base_context.get("transition_support") or {},
        "principles": base_context.get("principles") or [],
        "living_strategy_guardian": {
            "signals": strategy_context.get("signals") or {},
            "household": strategy_context.get("household") or {},
            "strategy_candidates": strategy_context.get("strategy_candidates") or [],
            "material_unknowns": strategy_context.get("material_unknowns") or [],
            "clarification_candidates": strategy_context.get("guardian_clarification_candidates") or [],
            "least_restrictive_safe_care_rule": bool(strategy_context.get("least_restrictive_safe_care_rule")),
            "policy": strategy_context.get("policy"),
            "rule": "These are Guardian constraints and candidate unknowns only. The AI decides whether and how to ask the next question.",
        },
        "readiness_guardian": {
            "rank_sensitive_unknowns": rank_sensitive_unknowns,
            "ready_veto_active": bool(rank_sensitive_unknowns),
            "rule": "READY is forbidden while an unresolved HIGH-information client fact is known to be capable of materially changing candidate ordering. Guardian identifies the decision dimension; Semantic AI chooses the next question.",
        },
        "user_statement_accounting": accounting,
        "material_unknown_policy": {
            "unknown_is_not_default": True,
            "no_silent_drop": True,
            "required_statement_coverage_percent": 100,
            "rule": "ASK_OR_RESEARCH_IF_MATERIAL_TO_ELIGIBILITY_ORDERING_TRADEOFF_OR_TRANSITION",
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


def _consult_semantic_ai(context: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    enabled = os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    required = os.getenv("OPTIME_SEMANTIC_AI_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    context["semantic_ai"] = {"enabled": enabled, "required": required, "status": "DISABLED"}

    # Deterministic rules never substitute for the interview AI. If AI is required but
    # unavailable, the interview blocks instead of falling back to scripted questions.
    if not enabled:
        context["adaptive_questions"] = []
        context["decision_readiness"] = "NEEDS_RESEARCH" if required else "NEEDS_CLARIFICATION"
        if required:
            context["semantic_ai"]["status"] = "REQUIRED_BUT_DISABLED"
        return context

    try:
        result = _call_semantic_ai(context, questionnaire_state, natural_language_query)
        readiness = str(result.get("decision_readiness") or "NEEDS_CLARIFICATION").upper()

        rank_sensitive_unknowns = list(((context.get("readiness_guardian") or {}).get("rank_sensitive_unknowns") or []))
        guardian_veto = readiness == "READY" and bool(rank_sensitive_unknowns)
        if guardian_veto:
            veto_packet = {
                "reason": "AI_READY_REJECTED_RANK_SENSITIVE_UNKNOWN",
                "unresolved": rank_sensitive_unknowns,
                "instruction": "Choose exactly one next client question that resolves the highest-impact unresolved decision dimension. Do not return READY until the dimension is resolved or explicitly acknowledged as no preference/not sure.",
            }
            second_result = _call_semantic_ai(
                context,
                questionnaire_state,
                natural_language_query,
                readiness_veto=veto_packet,
            )
            second_readiness = str(second_result.get("decision_readiness") or "NEEDS_CLARIFICATION").upper()
            second_question = str(second_result.get("next_question") or "").strip()
            if second_readiness == "NEEDS_CLARIFICATION" and second_question:
                result = second_result
                readiness = second_readiness
                context["readiness_guardian"]["veto_applied"] = True
                context["readiness_guardian"]["veto_resolution"] = "RETURNED_TO_SEMANTIC_AI_FOR_NEXT_BEST_QUESTION"
            else:
                result = second_result
                readiness = "NEEDS_RESEARCH"
                context["readiness_guardian"]["veto_applied"] = True
                context["readiness_guardian"]["veto_resolution"] = "AI_DID_NOT_RESOLVE_GUARDIAN_VETO"

        context["semantic_ai"] = {
            "enabled": True,
            "required": required,
            "status": "CONSULTED_AND_VALIDATED" if readiness != "NEEDS_RESEARCH" else ("GUARDIAN_BLOCKED_READY" if guardian_veto else "CONSULTED_AND_VALIDATED"),
            "result": result,
        }
        context["decision_readiness"] = readiness
        context["adaptive_questions"] = []

        next_question = str(result.get("next_question") or "").strip()
        if readiness == "NEEDS_CLARIFICATION" and next_question:
            question_key = _semantic_question_key(next_question)
            answered_keys = _answered_adaptive_keys(questionnaire_state)
            if question_key not in answered_keys and not _question_exists(context, question_key):
                context["adaptive_questions"] = [
                    _base._question(
                        question_key,
                        next_question,
                        "Governed Semantic AI selected this as the highest-information unresolved issue after consulting the Learning Center and Guardian context.",
                        ["client_intent_completeness", "preference_congruence"],
                        [],
                    )
                ]
        elif readiness in {"READY", "NEEDS_RESEARCH"}:
            context["adaptive_questions"] = []
    except Exception as exc:
        context["semantic_ai"] = {
            "enabled": True,
            "required": required,
            "status": "FAILED",
            "error": str(exc),
        }
        context["adaptive_questions"] = []
        context["decision_readiness"] = "NEEDS_RESEARCH" if required else "NEEDS_CLARIFICATION"
    return context


def build_human_intelligence_context(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    # Deterministic runtimes are retained only for signals/Guardian evidence. Any
    # hard-coded question lists they produce are deliberately discarded.
    base_context = _base.build_human_intelligence_context(questionnaire_state, natural_language_query)
    strategy_context = build_living_strategy_context(questionnaire_state, natural_language_query)
    context = _governed_context(base_context, strategy_context, natural_language_query)
    context["adaptive_questions"] = []
    context["decision_readiness"] = "NEEDS_CLARIFICATION"
    return _consult_semantic_ai(context, questionnaire_state, natural_language_query)


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
        band = _base._community_size_band(beds)
        fit = _base._size_fit(preference, band)
        row["human_person_fit"] = {
            "community_size": {
                "official_bed_count": beds if beds is not None else "UNKNOWN",
                "community_size_band": band,
                "preference": preference,
                "fit_score": fit if fit is not None else "UNKNOWN",
                "source": "Nevada HCQC / ALiS official detail" if beds is not None else "UNKNOWN",
                "evidence_class": "REGULATORY_VERIFIED" if beds is not None else "UNKNOWN",
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
