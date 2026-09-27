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


from app.services.intake_interpretation import _mentions_couple

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


from app.services.intake_interpretation import _duration_months

def build_living_strategy_context(questionnaire_state: Dict[str, Any], natural_language_query: str = "", *, care_denials=None, intake_facts=None) -> Dict[str, Any]:
    from app.services.intake_interpretation import extract_intake_facts
    facts = intake_facts if intake_facts is not None else extract_intake_facts(questionnaire_state, natural_language_query, care_denials=care_denials)
    questionnaire_state = facts["questionnaire_state"]
    sf = facts["strategy"]
    couple = sf["couple"]
    no_dementia = sf["no_dementia"]
    memory_care_needed = sf["memory_care_needed"]
    surgery = sf["surgery"]
    spine_or_back = sf["spine_or_back"]
    rehab = sf["rehab"]
    expected_recovery = sf["expected_recovery"]
    duration = sf["duration"]
    explicit_independence = sf["explicit_independence"]
    no_adl_support = sf["no_adl_support"]
    no_medication_support = sf["no_medication_support"]
    adl = sf["adl"]
    medication = sf["medication"]
    high_social = sf["high_social"]
    skilled_rehab_known = sf["skilled_rehab_known"]
    move_timing = sf["move_timing"]
    budget = sf["budget"]
    medicare = sf["medicare"]
    entrance_fee = sf["entrance_fee"]

    household = {
        "type": "COUPLE" if couple else "SINGLE_OR_UNKNOWN",
        "requires_two_resident_model": couple,
        "resident_profiles": [],
    }
    if couple:
        household["resident_profiles"] = [
            {
                "role": "HIGHER_NEED_PARTNER" if (adl or medication or memory_care_needed or rehab or surgery) else "PARTNER_A",
                "current_needs": [item for item, present in (("ADL_SUPPORT", adl), ("MEDICATION_SUPPORT", medication), ("MEMORY_CARE", memory_care_needed), ("REHABILITATION", rehab or surgery)) if present],
                "trajectory": "EXPECTED_IMPROVEMENT" if expected_recovery else "STABLE_OR_UNKNOWN",
                "expected_support_duration_months": duration if duration is not None else "UNKNOWN",
            },
            {
                "role": "OTHER_PARTNER",
                "current_needs": [],
                "trajectory": "STABLE_OR_UNKNOWN",
            },
        ]

    care_search_approach = facts["preferences"]["care_search_approach"]
    strategy_candidates: List[Dict[str, Any]] = []

    def add_strategy(strategy_id: str, status: str, rationale: str, required_capabilities: List[str], rank_hint: int) -> None:
        if any(row.get("strategy_id") == strategy_id for row in strategy_candidates):
            return
        strategy_candidates.append({
            "strategy_id": strategy_id,
            "status": status,
            "rationale": rationale,
            "required_capabilities": required_capabilities,
            "rank_hint": rank_hint,
        })

    independent_long_term_pattern = (
        explicit_independence
        and no_adl_support
        and not adl
        and not medication
        and no_dementia
        and not memory_care_needed
        and not surgery
        and not rehab
        and not skilled_rehab_known
    )
    if independent_long_term_pattern:
        add_strategy(
            "INDEPENDENT_LIVING",
            "LEADING",
            "The resident is explicitly fully independent, cognitively intact, and has no current care, rehabilitation, or nursing need. Independent Living is the least-restrictive primary residential strategy; higher-care settings should not outrank it merely because they have richer regulatory data.",
            ["INDEPENDENT_LIVING"],
            1,
        )
        add_strategy(
            "LIFE_PLAN_CCRC",
            "STRONG_OPTION",
            "A Life Plan/CCRC may be considered as a future-care planning option while the resident is still independent, subject to entrance-fee tolerance, contract terms, financial review, and medical underwriting where applicable.",
            ["INDEPENDENT_LIVING", "CONTINUUM_OF_CARE"],
            2,
        )

    if memory_care_needed:
        add_strategy(
            "MEMORY_CARE",
            "LEADING",
            "A stated dementia, Alzheimer’s, wandering, or material cognitive-impairment need requires a verified memory-care setting rather than ordinary Independent Living or generic Assisted Living.",
            ["MEMORY_CARE_CONFIRMED", "SECURE_COGNITIVE_SUPPORT", "ADL_SUPPORT_IF_NEEDED"],
            1,
        )
        if couple:
            add_strategy(
                "LIFE_PLAN_CCRC_WITH_MEMORY_CONTINUUM",
                "STRONG_OPTION",
                "For a couple with different care needs, a campus that can keep both partners nearby while providing verified memory care to the higher-need partner may preserve co-residence and continuity.",
                ["COUPLE_CORESIDENCE", "INDEPENDENT_OR_ASSISTED_LIVING", "MEMORY_CARE_CONFIRMED", "CONTINUUM_OF_CARE"],
                2,
            )

    transient_support_pattern = adl and no_dementia and not memory_care_needed and expected_recovery
    if transient_support_pattern:
        add_strategy(
            "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE",
            "LEADING_CONDITIONAL",
            "The care need appears temporary and primarily ADL-oriented. Independent Living plus temporary in-home/private-duty support may preserve the preferred lifestyle if the building permits outside care and clinical rehab needs are covered separately.",
            ["INDEPENDENT_LIVING", "OUTSIDE_CARE_ALLOWED", "ACCESSIBLE_UNIT", "SOCIAL_PROGRAMMING"],
            1,
        )
    if skilled_rehab_known or (surgery and spine_or_back):
        add_strategy(
            "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING",
            "LEADING_CONDITIONAL",
            "A post-operative recovery may require skilled PT/OT or short-stay rehabilitation before long-term residential placement. The rehab episode and the long-term living decision should not be conflated.",
            ["SKILLED_REHAB_OR_PT_OT", "DISCHARGE_PLAN", "INDEPENDENT_LIVING_AFTER_RECOVERY"],
            1,
        )
    if couple and (high_social or expected_recovery) and not memory_care_needed:
        add_strategy(
            "LIFE_PLAN_CCRC",
            "STRONG_OPTION",
            "A Life Plan/CCRC can let a couple remain in one community while one partner temporarily or later needs a higher care level, while preserving richer independent-living amenities.",
            ["COUPLE_CORESIDENCE", "INDEPENDENT_LIVING", "ASSISTED_LIVING", "SKILLED_NURSING_OR_REHAB", "SOCIAL_PROGRAMMING"],
            2,
        )
    if adl and not memory_care_needed:
        add_strategy(
            "ASSISTED_LIVING",
            "VALID_OPTION" if transient_support_pattern else "LEADING",
            "Assisted Living directly supplies ADL support. It should lead for persistent non-skilled daily-care needs, but should not automatically outrank lower-intensity strategies when the need is temporary and recovery is expected.",
            ["ADL_SUPPORT", "MEDICATION_SUPPORT_IF_NEEDED", "SOCIAL_PROGRAMMING"],
            3 if transient_support_pattern else 1,
        )
    elif medication and not memory_care_needed and not skilled_rehab_known:
        add_strategy(
            "ASSISTED_LIVING",
            "LEADING_CONDITIONAL",
            "Medication-management support is a residential-care need that Independent Living alone does not establish. Assisted Living should lead unless a verified outside-care model safely covers the need.",
            ["MEDICATION_SUPPORT", "ADL_SUPPORT_IF_NEEDED"],
            1,
        )
        add_strategy(
            "INDEPENDENT_LIVING_PLUS_OUTSIDE_CARE",
            "ALTERNATIVE_CONDITIONAL",
            "Independent Living may remain viable only where medication support can be safely supplied through a verified outside-care pathway.",
            ["INDEPENDENT_LIVING", "OUTSIDE_CARE_ALLOWED", "MEDICATION_SUPPORT_EXTERNAL"],
            2,
        )
    if skilled_rehab_known:
        add_strategy(
            "SHORT_STAY_SKILLED_NURSING_REHAB",
            "EPISODIC_OPTION",
            "Short-stay skilled rehabilitation may be appropriate for the recovery episode if clinically indicated and covered, but it is not necessarily the long-term residence.",
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
            "Does the surgeon or rehabilitation team say the resident needs skilled rehabilitation/physical or occupational therapy, or only help with daily tasks such as bathing and dressing?",
            "This can materially change the care strategy.",
            ["Skilled PT/OT or rehabilitation", "Only personal-care help", "Both", "Not sure"],
        ))
    if (surgery or rehab) and medicare in {"", "unknown", "not sure", "unsure"}:
        clarification_candidates.append(_question(
            "medicare_status",
            "Does the resident have Medicare, and if so is it Original Medicare or Medicare Advantage?",
            "Coverage and network rules can materially change post-acute rehabilitation and home-health options.",
            ["Original Medicare", "Medicare Advantage", "No Medicare", "Not sure"],
        ))
    if expected_recovery and not move_timing:
        clarification_candidates.append(_question(
            "move_timing_vs_rehab",
            "Should the move to senior living happen during recovery, or after most rehabilitation is complete?",
            "The strategy can differ between an immediate move and a move after functional recovery.",
            ["Move during recovery", "Finish rehabilitation first", "Flexible", "Not sure"],
        ))
    if budget in (None, "", 0):
        clarification_candidates.append(_question(
            "monthly_budget",
            "What monthly housing-and-care budget is comfortable?",
            "Different living-and-care strategies have materially different cost structures.",
            ["Under $5,000", "$5,000-$8,000", "$8,000-$12,000", "Above $12,000", "Not sure"],
        ))
    if couple and entrance_fee in {"", "unknown", "not sure", "unsure"}:
        clarification_candidates.append(_question(
            "ccrc_entrance_fee_tolerance",
            "Would the couple consider a Life Plan/CCRC that may require a substantial one-time entrance fee in exchange for a continuum of care?",
            "This determines whether Life Plan communities should compete with monthly-rental options.",
            ["Yes", "No", "Depends on amount/terms", "Not sure"],
        ))

    strategy_candidates.sort(key=lambda row: (int(row.get("rank_hint") or 99), str(row.get("strategy_id") or "")))
    unresolved = [q["question_key"] for q in clarification_candidates]

    strategy = {
        "version": "living-strategy-runtime-v1.3-decision-quality",
        "household": household,
        "signals": {
            "post_surgical": surgery,
            "spine_or_back_surgery": spine_or_back,
            "rehabilitation_need_detected": rehab or surgery,
            "expected_recovery": expected_recovery,
            "temporary_support_duration_months": duration if duration is not None else "UNKNOWN",
            "adl_support_needed": adl,
            "medication_support_needed": medication,
            "memory_care_needed": memory_care_needed,
            "high_social_culture_priority": high_social,
            "no_dementia": no_dementia,
            "explicit_independence": explicit_independence,
            "care_search_approach": care_search_approach or "UNSPECIFIED",
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

    from app.services.living_strategy_guard_patch import deceased_spouse_without_current_couple, _strip_couple_only_strategy
    if facts["deceased_spouse_without_current_couple"]:
        return _strip_couple_only_strategy(strategy)
    return strategy


__all__ = ["build_living_strategy_context"]
