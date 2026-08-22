from __future__ import annotations

"""Governed living-and-care strategy layer.

This module decides *which type of solution* should be considered before ranking
individual facilities. It deliberately separates current needs, recovery trajectory,
household, lifestyle, and financing facts.

IMPORTANT: this layer does not interview the user. It may identify material unknowns
and proposed clarification candidates for the Guardian context, but Semantic AI owns
the actual question selection and sequence. UNKNOWN remains UNKNOWN.
"""

import re
from typing import Any, Dict, List


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def _first_known(questionnaire: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = questionnaire.get(key)
        if value not in (None, ""):
            return value
    return None


def _hi(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    value = questionnaire.get("humanIntelligenceV2")
    return value if isinstance(value, dict) else {}


def _question(key: str, text: str, why: str, options: List[str]) -> Dict[str, Any]:
    return {
        "question_key": key,
        "question": text,
        "why_it_matters": why,
        "options": options,
        "source": "living_strategy_runtime_v1",
        "role": "GUARDIAN_CLARIFICATION_CANDIDATE_ONLY",
    }


def _duration_months(text: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*(?:month|months|mo)\b", text)
    if match:
        return int(match.group(1))
    if _contains(text, "three months", "3 months"):
        return 3
    return None


def build_living_strategy_context(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    query = _norm(natural_language_query)
    hi = _hi(questionnaire_state)
    transition = hi.get("transitionRiskProfile") if isinstance(hi.get("transitionRiskProfile"), dict) else {}
    finance = hi.get("financialProfile") if isinstance(hi.get("financialProfile"), dict) else {}

    couple = _contains(query, "couple", "husband", "wife", "spouse", "both of us", "both parents", "parents")
    if _norm(questionnaire_state.get("relationship")) in {"wife", "husband", "spouse"}:
        couple = True

    no_dementia = _contains(query, "no dementia", "without dementia", "mentally alert", "cognitively intact", "no memory concerns", "no memory concern", "does not need cognitive support", "doesn't need cognitive support", "no cognitive support") or _norm(questionnaire_state.get("memoryStatus")) in {"no", "none", "no dementia", "no memory concerns"}

    surgery = _contains(query, "surgery", "operation", "post-op", "postoperative")
    spine_or_back = _contains(query, "spine", "spinal", "back surgery", "back operation")
    rehab = _contains(query, "rehab", "rehabilitation", "physical therapy", "physiotherapy", "pt ", " pt", "occupational therapy")
    expected_recovery = _contains(query, "expected to walk", "should walk again", "return to walking", "expected to recover", "temporary", "short-term", "short term")
    duration = _duration_months(query)
    if duration is not None and duration <= 6:
        expected_recovery = True

    explicit_independence = _contains(query, "fully independent", "completely independent", "independent with bathing", "independent with dressing", "independent with toileting", "independent with transfers") or _contains(_norm(questionnaire_state.get("assistanceLevel")), "fully independent", "independent")
    no_adl_support = explicit_independence or _contains(query, "no adl support", "no help with daily activities", "does not need help with daily activities", "doesn't need help with daily activities", "no personal care support")
    no_medication_support = (explicit_independence and _contains(query, "medication", "medications", "medicine")) or _contains(query, "no medication support", "no medication assistance", "does not need medication support", "doesn't need medication support")
    adl = (not no_adl_support) and (_contains(query, "bathing", "dressing", "shower", "toileting", "adl", "personal care") or _contains(_norm(questionnaire_state.get("assistanceLevel")), "bathing", "dressing", "assistance"))
    medication = (not no_medication_support) and _contains(query, "medication", "medications", "medicine")
    high_social = _contains(query, "culture", "cultural", "classes", "activities", "social", "clubs", "lectures", "music", "art", "events")

    raw_rehab_need = _norm(transition.get("postHospitalRehabNeed"))
    skilled_rehab_known = raw_rehab_need in {"yes", "required", "high"} or _contains(query, "physical therapy", "occupational therapy", "skilled rehab", "rehabilitation")

    move_timing = _norm(transition.get("moveTiming") or questionnaire_state.get("moveTiming"))
    budget = _first_known(questionnaire_state, "budget", "monthlyBudget")
    medicare = _norm(finance.get("medicareStatus") or questionnaire_state.get("medicareStatus"))
    entrance_fee = _norm(finance.get("entranceFeeTolerance") or questionnaire_state.get("entranceFeeTolerance"))

    household = {
        "type": "COUPLE" if couple else "SINGLE_OR_UNKNOWN",
        "requires_two_resident_model": couple,
        "resident_profiles": [],
    }
    if couple:
        household["resident_profiles"] = [
            {
                "role": "RECOVERING_PARTNER",
                "current_needs": [item for item, present in (("ADL_SUPPORT", adl), ("MEDICATION_SUPPORT", medication), ("REHABILITATION", rehab or surgery)) if present],
                "trajectory": "EXPECTED_IMPROVEMENT" if expected_recovery else "UNKNOWN",
                "expected_support_duration_months": duration if duration is not None else "UNKNOWN",
            },
            {
                "role": "OTHER_PARTNER",
                "current_needs": [],
                "trajectory": "STABLE_OR_UNKNOWN",
            },
        ]

    strategy_candidates: List[Dict[str, Any]] = []

    def add_strategy(strategy_id: str, status: str, rationale: str, required_capabilities: List[str], rank_hint: int) -> None:
        strategy_candidates.append({
            "strategy_id": strategy_id,
            "status": status,
            "rationale": rationale,
            "required_capabilities": required_capabilities,
            "rank_hint": rank_hint,
        })

    transient_support_pattern = adl and no_dementia and expected_recovery
    if transient_support_pattern:
        add_strategy(
            "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE",
            "LEADING_CONDITIONAL",
            "The care need appears temporary and primarily ADL-oriented. Independent Living plus temporary in-home/private-duty support may preserve the couple's preferred lifestyle if the building permits outside care and clinical rehab needs are covered separately.",
            ["INDEPENDENT_LIVING", "OUTSIDE_CARE_ALLOWED", "ACCESSIBLE_UNIT", "SOCIAL_PROGRAMMING"],
            1,
        )
    if skilled_rehab_known or (surgery and spine_or_back):
        add_strategy(
            "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING",
            "LEADING_CONDITIONAL",
            "A post-operative spine recovery may require skilled PT/OT or short-stay rehabilitation before long-term residential placement. The rehab episode and the long-term living decision should not be conflated.",
            ["SKILLED_REHAB_OR_PT_OT", "DISCHARGE_PLAN", "INDEPENDENT_LIVING_AFTER_RECOVERY"],
            1,
        )
    if couple and (high_social or expected_recovery):
        add_strategy(
            "LIFE_PLAN_CCRC",
            "STRONG_OPTION",
            "A Life Plan/CCRC can let a couple remain in one community while one partner temporarily or later needs a higher care level, while preserving richer independent-living amenities.",
            ["COUPLE_CORESIDENCE", "INDEPENDENT_LIVING", "ASSISTED_LIVING", "SKILLED_NURSING_OR_REHAB", "SOCIAL_PROGRAMMING"],
            2,
        )
    if adl:
        add_strategy(
            "ASSISTED_LIVING",
            "VALID_OPTION",
            "Assisted Living directly supplies ADL support, but it should not automatically outrank lower-intensity strategies when the need is temporary and recovery is expected.",
            ["ADL_SUPPORT", "MEDICATION_SUPPORT_IF_NEEDED", "SOCIAL_PROGRAMMING"],
            3 if transient_support_pattern else 1,
        )
    if skilled_rehab_known:
        add_strategy(
            "SHORT_STAY_SKILLED_NURSING_REHAB",
            "EPISODIC_OPTION",
            "Short-stay skilled rehabilitation may be appropriate for the recovery episode if clinically indicated and covered, but it is not necessarily the couple's long-term residence.",
            ["SKILLED_NURSING", "PT", "OT", "DISCHARGE_PLANNING"],
            2,
        )

    if not strategy_candidates:
        add_strategy(
            "ASSISTED_OR_INDEPENDENT_LIVING_UNRESOLVED",
            "NEEDS_CLARIFICATION",
            "The available facts are insufficient to choose the least-restrictive safe living strategy.",
            [],
            9,
        )

    clarification_candidates: List[Dict[str, Any]] = []
    if (surgery or rehab) and not skilled_rehab_known:
        clarification_candidates.append(_question(
            "rehab_level_needed",
            "Does the surgeon or rehabilitation team say he needs skilled rehabilitation/physical or occupational therapy, or only help with daily tasks such as bathing and dressing?",
            "This can materially change the care strategy.",
            ["Skilled PT/OT or rehabilitation", "Only personal-care help", "Both", "Not sure"],
        ))
    if (surgery or rehab) and medicare in {"", "unknown", "not sure", "unsure"}:
        clarification_candidates.append(_question(
            "medicare_status",
            "Does he have Medicare, and if so is it Original Medicare or Medicare Advantage?",
            "Coverage and network rules can materially change post-acute rehabilitation and home-health options.",
            ["Original Medicare", "Medicare Advantage", "No Medicare", "Not sure"],
        ))
    if expected_recovery and not move_timing:
        clarification_candidates.append(_question(
            "move_timing_vs_rehab",
            "Do they want to move to the senior community during the recovery period, or finish most of the rehabilitation first and move afterward?",
            "The strategy can differ between an immediate move and a move after functional recovery.",
            ["Move during recovery", "Finish rehabilitation first", "Flexible", "Not sure"],
        ))
    if budget in (None, "", 0):
        clarification_candidates.append(_question(
            "monthly_budget",
            "What monthly housing-and-care budget are they comfortable with?",
            "Different living-and-care strategies have materially different cost structures.",
            ["Under $5,000", "$5,000-$8,000", "$8,000-$12,000", "Above $12,000", "Not sure"],
        ))
    if couple and entrance_fee in {"", "unknown", "not sure", "unsure"}:
        clarification_candidates.append(_question(
            "ccrc_entrance_fee_tolerance",
            "Would they consider a Life Plan/CCRC that may require a substantial one-time entrance fee in exchange for a continuum of care?",
            "This determines whether Life Plan communities should compete with monthly-rental options.",
            ["Yes", "No", "Depends on amount/terms", "Not sure"],
        ))

    strategy_candidates.sort(key=lambda row: (int(row.get("rank_hint") or 99), str(row.get("strategy_id") or "")))
    unresolved = [q["question_key"] for q in clarification_candidates]

    return {
        "version": "living-strategy-runtime-v1.1-ai-governed",
        "household": household,
        "signals": {
            "post_surgical": surgery,
            "spine_or_back_surgery": spine_or_back,
            "rehabilitation_need_detected": rehab or surgery,
            "expected_recovery": expected_recovery,
            "temporary_support_duration_months": duration if duration is not None else "UNKNOWN",
            "adl_support_needed": adl,
            "medication_support_needed": medication,
            "high_social_culture_priority": high_social,
            "no_dementia": no_dementia,
        },
        "strategy_candidates": strategy_candidates,
        "material_questions": [],
        "guardian_clarification_candidates": clarification_candidates,
        "material_unknowns": unresolved,
        "decision_readiness": "NEEDS_STRATEGY_CLARIFICATION" if unresolved else "STRATEGY_READY",
        "least_restrictive_safe_care_rule": True,
        "interview_owner": "SEMANTIC_AI",
        "policy": "Choose the least-restrictive safe living-and-care strategy before ranking facilities; separate temporary recovery care from long-term residence; never convert a material unknown into a default. Strategy rules may flag unknowns but may not directly ask the user questions.",
    }


__all__ = ["build_living_strategy_context"]
