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


_COUPLE_NEGATION_WORDS = {"no", "not", "without", "single", "widow", "widower", "unmarried", "divorced"}
_COUPLE_RELATIONSHIP_WORDS = ("husband", "wife", "spouse", "parents")


def _mentions_couple(text: str) -> bool:
    """True only for a genuine couple/relationship signal.

    A naive substring check on "couple" fires on the idiomatic "a couple of X" (weeks,
    specific things, ...), which has nothing to do with a relationship, and fires on
    "spouse"/"husband"/"wife" even when the sentence explicitly negates them ("no
    spouse", "without a husband") -- both produced a false COUPLE_CORESIDENCE MUST and
    a spurious CCRC entrance-fee guardian question for single-person searches.
    """
    if re.search(r"\bcouple\b(?!\s+of\b)", text):
        return True
    if _contains(text, "both of us", "both parents"):
        return True
    for word in _COUPLE_RELATIONSHIP_WORDS:
        for match in re.finditer(rf"\b{word}\b", text):
            preceding_words = text[: match.start()].split()[-3:]
            if any(negation in preceding_words for negation in _COUPLE_NEGATION_WORDS):
                continue
            return True
    return False


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

    couple = _mentions_couple(query)
    if _norm(questionnaire_state.get("relationship")) in {"wife", "husband", "spouse"}:
        couple = True

    no_dementia = _contains(query, "no dementia", "without dementia", "mentally alert", "cognitively intact", "no memory concerns", "no memory concern", "does not need cognitive support", "doesn't need cognitive support", "no cognitive support") or _norm(questionnaire_state.get("memoryStatus")) in {"no", "none", "no dementia", "no memory concerns"}
    memory_care_needed = (
        not no_dementia
        and _contains(query, "dementia", "alzheimer", "memory care", "wandering", "cognitive decline", "cognitive impairment")
    ) or _norm(questionnaire_state.get("memoryStatus")) in {"yes", "dementia", "memory care", "alzheimer", "alzheimers"}

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

    return {
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
