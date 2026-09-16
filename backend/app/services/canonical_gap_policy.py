from __future__ import annotations

"""Deterministic authority for client-intent gaps.

Semantic AI may extract a possible gap and phrase a question.  It is never the
authority for whether that gap blocks recommendations, changes final readiness,
or requires escalation.  Those decisions are derived here from a stable gap key,
canonical client facts, and governed decision context.
"""

import re
from enum import Enum
from typing import Any, Dict, Iterable, List


class GapClassification(str, Enum):
    BLOCKING = "BLOCKING"
    IMPORTANT_NON_BLOCKING = "IMPORTANT_NON_BLOCKING"
    PREFERENCE = "PREFERENCE"


_BLOCKING_GAPS = {
    "market_location",
    "monthly_affordability",
    "monthly_budget",
    "rehab_level_needed",
    "medicare_status",
}

_IMPORTANT_NON_BLOCKING_GAPS = {
    "cohabitation_requirement",
    "loneliness_severity",
    "social_interaction_need_after_loss",
    "move_participation",
    "move_timing_vs_rehab",
}

_PREFERENCE_GAPS = {
    "community_size_preference",
    "ccrc_entrance_fee_tolerance",
}

_PARAMETER_ALIASES = {
    "budget": "monthly_budget",
    "monthly_affordability": "monthly_budget",
    "co_residence": "cohabitation_requirement",
    "coresidence": "cohabitation_requirement",
    "couple_coresidence": "cohabitation_requirement",
    "same_apartment": "cohabitation_requirement",
    "same_campus": "cohabitation_requirement",
    "social_interaction_need_after_loss": "loneliness_severity",
    "social_transition_fit": "loneliness_severity",
}


def canonical_client_facts(questionnaire_state: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    text = " ".join(str(user_text or "").lower().split())
    relationship = str(questionnaire_state.get("relationship") or "").lower()
    household_is_couple = bool(
        relationship in {"spouse", "partner", "husband", "wife"}
        or re.search(r"\b(?:married couple|couple|husband and wife|spouses?|partners?)\b", text)
    )
    different_care_needs = bool(
        household_is_couple
        and (
            re.search(r"\bone (?:spouse|partner|person)[^.]{0,100}\b(?:other|another)\b", text)
            or re.search(r"\bdifferent care needs?\b", text)
            or ("independent" in text and re.search(r"\bneeds? (?:daily |personal )?(?:care|help|assistance)\b", text))
        )
    )
    same_home_is_must = bool(
        re.search(
            r"\b(?:same (?:apartment|unit|home|room)[^.]{0,35}(?:must|required|mandatory|non-negotiable)|"
            r"stay(?:ing)? in (?:the )?same (?:apartment|unit|home|room)[^.]{0,35}(?:must|required|mandatory|non-negotiable)|"
            r"(?:must|required|mandatory|non-negotiable)[^.]{0,35}same (?:apartment|unit|home|room)|"
            r"(?:cannot|can't|will not) (?:be )?separat(?:e|ed))\b",
            text,
        )
    )
    explicit_immediate_safety_risk = bool(
        re.search(r"\b(?:harm (?:herself|himself|themself|myself)|suicid(?:e|al)|not safe alone (?:today|tonight|now)|immediate danger)\b", text)
    )
    return {
        "household_is_couple": household_is_couple,
        "different_care_needs": different_care_needs,
        "same_home_is_must": same_home_is_must,
        "explicit_immediate_safety_risk": explicit_immediate_safety_risk,
    }


def normalize_gap_key(value: Any) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if not key:
        return ""
    if key in _PARAMETER_ALIASES:
        return _PARAMETER_ALIASES[key]
    for token, canonical in _PARAMETER_ALIASES.items():
        if token in key:
            return canonical
    return key


def classify_gap(gap_key: str, canonical_facts: Dict[str, Any], decision_context: Dict[str, Any]) -> GapClassification:
    key = normalize_gap_key(gap_key)
    if key == "cohabitation_requirement":
        if canonical_facts.get("household_is_couple") and canonical_facts.get("different_care_needs") and canonical_facts.get("same_home_is_must"):
            return GapClassification.BLOCKING
        return GapClassification.IMPORTANT_NON_BLOCKING
    if key == "loneliness_severity":
        return GapClassification.IMPORTANT_NON_BLOCKING
    if key in _BLOCKING_GAPS:
        return GapClassification.BLOCKING
    if key in _IMPORTANT_NON_BLOCKING_GAPS:
        return GapClassification.IMPORTANT_NON_BLOCKING
    if key in _PREFERENCE_GAPS:
        return GapClassification.PREFERENCE
    # A Guardian-owned HIGH information gap is governed input, not an AI vote.
    if decision_context.get("source") in {"HUMAN_INTELLIGENCE_GUARDIAN", "LIVING_STRATEGY_GUARDIAN"}:
        return GapClassification.BLOCKING
    # An unregistered model-proposed gap may be preserved for later learning but
    # cannot acquire recommendation-control authority merely because the model
    # labelled it MUST or returned NEEDS_CLARIFICATION.
    return GapClassification.IMPORTANT_NON_BLOCKING


def _statement_gap_key(statement: Dict[str, Any]) -> str:
    for field in ("gap_key", "target_fact_key"):
        value = normalize_gap_key(statement.get(field))
        if value:
            return value
    for value in statement.get("mapped_parameters") or []:
        normalized = normalize_gap_key(value)
        if normalized:
            return normalized
    return ""


def assess_gaps(
    *,
    guardian_gaps: Iterable[Dict[str, Any]],
    ai_result: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    user_text: str,
) -> Dict[str, Any]:
    facts = canonical_client_facts(questionnaire_state, user_text)
    rows: List[Dict[str, Any]] = []

    for gap in guardian_gaps:
        if not isinstance(gap, dict):
            continue
        key = normalize_gap_key(gap.get("fact_key"))
        if not key:
            continue
        classification = classify_gap(key, facts, gap)
        rows.append({
            "gap_key": key,
            "classification": classification.value,
            "source": str(gap.get("source") or "GUARDIAN"),
            "reason": str(gap.get("reason") or ""),
        })

    for statement in ai_result.get("statements") or []:
        if not isinstance(statement, dict) or str(statement.get("status") or "").upper() != "ASKED":
            continue
        key = _statement_gap_key(statement)
        if not key:
            key = normalize_gap_key(ai_result.get("selected_fact_key")) or "semantic_ai_unregistered_gap"
        classification = classify_gap(key, facts, {"source": "SEMANTIC_AI"})
        rows.append({
            "gap_key": key,
            "classification": classification.value,
            "source": "SEMANTIC_AI",
            "reason": str(statement.get("meaning") or statement.get("raw_text") or ""),
        })

    deduped: Dict[str, Dict[str, Any]] = {}
    weight = {GapClassification.PREFERENCE.value: 1, GapClassification.IMPORTANT_NON_BLOCKING.value: 2, GapClassification.BLOCKING.value: 3}
    for row in rows:
        prior = deduped.get(row["gap_key"])
        if prior is None or weight[row["classification"]] > weight[prior["classification"]]:
            deduped[row["gap_key"]] = row

    assessments = sorted(deduped.values(), key=lambda row: (-weight[row["classification"]], row["gap_key"]))
    blocking_keys = [row["gap_key"] for row in assessments if row["classification"] == GapClassification.BLOCKING.value]
    escalation_required = bool(facts.get("explicit_immediate_safety_risk"))
    return {
        "version": "canonical-gap-policy-v1",
        "authority": "DETERMINISTIC_POLICY",
        "canonical_facts": facts,
        "assessments": assessments,
        "blocking_gap_keys": blocking_keys,
        "escalation_required": escalation_required,
        "escalation_reason": "EXPLICIT_IMMEDIATE_SAFETY_RISK" if escalation_required else None,
    }


__all__ = [
    "GapClassification",
    "assess_gaps",
    "canonical_client_facts",
    "classify_gap",
    "normalize_gap_key",
]
