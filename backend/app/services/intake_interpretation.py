from __future__ import annotations

"""The only intake interpretation boundary.

Extract source facts once per answer revision. Strategy, person-fit, intent and
care-delivery consumers receive projections of this record, never reinterpret
the story. Evidence/clinical guardrails and AI packet validation remain separate
from fact extraction. A confirmed profile is sealed and reused without another
model call or extraction. No facility evidence or ranking rules live here.
"""

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List
from app.services.care_input_assertions import extract_care_denials, without_negated_nursing

def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower()


def _nested(payload: Dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _contains_any(value: Any, tokens: Iterable[str]) -> bool:
    text = _norm(value)
    return any(token.lower() in text for token in tokens)


def _explicit_high(value: Any) -> bool:
    return _contains_any(value, ("high", "very important", "important", "strong", "frequent", "daily", "yes", "needed", "need", "often", "helpful"))


def _explicit_low(value: Any) -> bool:
    return _contains_any(value, ("low", "not important", "rare", "minimal", "no", "none", "overwhelming"))


def _explicit_neutral(value: Any) -> bool:
    return _contains_any(value, ("neither", "neutral", "about the same", "no strong preference"))



def _map_natural_language(text: str, needs_by_id: Dict[str, Any], *, care_denials=None) -> Dict[str, Any]:
    from app.services.decision_engine_core import _normalize, _add_need
    normalized = _normalize(text)
    extraction_meta = {"text": text, "recognized_tokens": [], "unrecognized_segments": []}

    # A monthly budget stated in the opening story is just as explicit as one
    # entered in a structured field.  The adaptive interview may carry the
    # original story forward without copying it into questionnaire["budget"],
    # so preserve the resulting pricing-verification requirement here.
    has_explicit_budget = bool(
        re.search(r"\$\s*\d[\d,]*(?:\.\d+)?", normalized)
        or re.search(
            r"\b(?:budget|spend|afford|monthly|per\s+month)\b[^.\n]{0,60}\b\d[\d,]*(?:\.\d+)?\b",
            normalized,
        )
    )
    if has_explicit_budget:
        _add_need(
            needs_by_id,
            "published_rates",
            "PREFERENCE",
            "KNOWN",
            ["KNOWN", "UNKNOWN"],
            "FACILITY",
            "natural_language.budget",
            1.0,
            "Current pricing must be checked against the stated budget",
        )
        extraction_meta["recognized_tokens"].append("budget")

    medicaid_negated = bool(
        re.search(
            r"\b(?:no|not|without|does\s+not|doesn't|will\s+not|won't)\b[^.!?\n]{0,50}\bmedicaid\b"
            r"|\bmedicaid\b[^.!?\n]{0,40}\b(?:not\s+(?:needed|required|applicable)|isn't\s+(?:needed|required|applicable))\b",
            normalized,
        )
    )
    if "medicaid" in normalized and not medicaid_negated:
        _add_need(
            needs_by_id,
            "medicaid_attributes",
            "PREFERENCE",
            "YES",
            ["YES", "UNKNOWN"],
            "FACILITY",
            "natural_language.medicaid",
            1.0,
            "Medicaid/payment pathway must be confirmed",
        )
        extraction_meta["recognized_tokens"].append("medicaid")

    def present(token: str) -> bool:
        token = token.lower()
        if "nursing" in token:
            return token in without_negated_nursing(normalized)
        if token in {"pt", "ot"}:
            return re.search(rf"\b{re.escape(token)}\b", normalized) is not None
        return token in normalized

    denials = care_denials if care_denials is not None else extract_care_denials(text)
    explicit_independence = denials["independent"]
    no_adl_support = denials["adl"]
    no_medication_support = denials["medication"]
    no_transfer_support = explicit_independence or any(phrase in normalized for phrase in (
        "no mobility limitation", "no mobility limitations", "walks independently", "no transfer assistance", "does not need transfer assistance",
        "does not need help getting", "doesn't need help getting", "no help getting",
        "does not need one person", "doesn't need one person",
        "does not need help getting", "doesn't need help getting",
        "does not need help to get", "doesn't need help to get",
    ))
    bed_or_shower_help = re.search(
        r"\b(?:needs?\s+(?:one person\s+to\s+)?help|needs?\s+one person\s+to\s+help\s+(?:her|him|them)|help\s+(?:her|him|them))\s+(?:to\s+)?(?:get|getting)\s+(?:in\s+and\s+out\s+of|into|out\s+of)\s+(?:the\s+)?(?:bed|shower)\b",
        normalized,
    )
    if bed_or_shower_help and not no_transfer_support:
        _add_need(needs_by_id, "transfer_assistance", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.9, "Transfer assistance support")
        extraction_meta["recognized_tokens"].append("bed or shower transfer help")
    no_memory_support = denials["memory"]
    no_clinical_support = any(phrase in normalized for phrase in (
        "no special medical or nursing needs", "no medical or nursing needs", "does not need nursing support", "doesn't need nursing support",
    ))
    no_dialysis = any(phrase in normalized for phrase in (
        "no dialysis", "not on dialysis", "does not need dialysis", "doesn't need dialysis",
    ))
    no_wound_care = any(phrase in normalized for phrase in (
        "no wound", "no wounds", "no wound care", "does not need wound care", "doesn't need wound care",
        "no pressure wound", "no pressure ulcer", "no pressure sore", "without pressure wounds",
        "does not need dressing changes", "doesn't need dressing changes", "no daily dressing changes",
        "does not have a pressure wound", "doesn't have a pressure wound",
    ))
    no_respiratory_support = any(phrase in normalized for phrase in (
        "no oxygen", "not on oxygen", "no continuous oxygen", "no respiratory support",
        "does not need oxygen", "doesn't need oxygen",
    ))
    no_speech_support = any(phrase in normalized for phrase in (
        "no speech", "no swallowing or speech", "does not need speech therapy",
        "doesn't need speech therapy", "without speech problems",
    ))

    keyword_rules = [
        (["stroke", "neurolog"], ("post_stroke_neuro_evidence", "HIGH", "YES", ["YES"], "PROGRAM", "natural_language", 0.95, "Post-stroke/neurological rehabilitation support")),
        (["dialysis"], ("dialysis_arrangements", "REQUIRED", "YES", ["YES"], "SERVICE", "natural_language", 0.98, "Dialysis arrangements required")),
        (["wound care", "wound management", "pressure wound", "pressure ulcer", "pressure sore", "daily dressing changes", "daily skilled dressing changes"], ("wound_care", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.98, "Wound-care capability required")),
        (["continuous oxygen", "oxygen"], ("respiratory_trach_vent", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.95, "Respiratory / oxygen support required")),
        (["24/7 nursing", "24x7 nursing", "round the clock nursing", "skilled nursing"], ("nursing_24_7", "REQUIRED", "YES", ["YES"], "FACILITY", "natural_language", 0.98, "24/7 nursing required")),
        (["physical therapy", "pt"], ("pt", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.95, "Physical therapy support")),
        (["occupational therapy", "ot"], ("ot", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.95, "Occupational therapy support")),
        (["speech therapy", "speech"], ("speech_therapy", "HIGH", "YES", ["YES", "UNKNOWN"], "SERVICE", "natural_language", 0.9, "Speech therapy support")),
        (["transfer", "mobility", "lift"], ("transfer_assistance", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.9, "Transfer assistance support")),
        (["bathing", "dressing", "adl"], ("adl_support", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.9, "ADL support")),
        (["medication"], ("medication_support", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.92, "Medication management support")),
        (["dementia", "alzheimer", "memory care"], ("memory_care", "HIGH", "YES", ["YES"], "PROGRAM", "natural_language", 0.95, "Memory care capability")),
        (["no dementia", "mentally alert", "no memory concerns", "no cognitive support"], ("memory_care", "PREFERENCE", "NO", ["NO", "UNKNOWN"], "PROGRAM", "natural_language", 0.85, "No dementia-focused unit specifically required")),
    ]
    suppressed_positive = {
        "adl_support": no_adl_support,
        "medication_support": no_medication_support,
        "transfer_assistance": no_transfer_support,
        "memory_care": no_memory_support,
        "nursing_24_7": no_clinical_support,
        "dialysis_arrangements": no_dialysis,
        "wound_care": no_wound_care,
        "respiratory_trach_vent": no_respiratory_support,
        "speech_therapy": no_speech_support,
    }
    for keywords, need_tuple in keyword_rules:
        parameter_id = need_tuple[0]
        desired_value = need_tuple[2]
        if desired_value == "YES" and suppressed_positive.get(parameter_id, False):
            continue
        if any(present(keyword) for keyword in keywords):
            _add_need(needs_by_id, *need_tuple)
            if parameter_id == "nursing_24_7" and not no_clinical_support:
                _add_need(needs_by_id, "skilled_nursing_capabilities", "REQUIRED", "YES", ["YES"], "FACILITY", "natural_language", 0.95, "Skilled nursing capability required")
            extraction_meta["recognized_tokens"].append(keywords[0])

    location_city = None
    for city in ["north las vegas", "las vegas", "henderson", "miami", "hialeah", "doral", "aventura", "homestead", "coral gables", "north miami"]:
        if city in normalized:
            location_city = city.upper()
            extraction_meta["recognized_tokens"].append(city)
            break
    return {"extraction": extraction_meta, "location_city": location_city}

def _extract_clinical_profile(questionnaire_state: Dict[str, Any], natural_language_query: str = "", *, care_denials=None) -> Dict[str, Any]:
    from app.services.decision_engine_core import (
        _map_assistance_level, _map_structured_medical_needs, _map_structured_follow_ups,
        _map_memory, _map_rehab, _map_personal_preferences, _map_financial, REQUIREMENT_WEIGHTS,
    )
    needs_by_id = {}

    _map_assistance_level(questionnaire_state, needs_by_id)
    _map_structured_medical_needs(questionnaire_state, needs_by_id)
    _map_structured_follow_ups(questionnaire_state, needs_by_id)
    _map_memory(questionnaire_state, needs_by_id)
    _map_rehab(questionnaire_state, needs_by_id)
    _map_personal_preferences(questionnaire_state, needs_by_id)
    _map_financial(questionnaire_state, needs_by_id)

    nl_meta = _map_natural_language(natural_language_query or "", needs_by_id, care_denials=care_denials)

    needs = [
        {
            "parameter_id": item.parameter_id,
            "requirement_level": item.requirement_level,
            "desired_value": item.desired_value,
            "acceptable_values": item.acceptable_values,
            "applicable_scope": item.applicable_scope,
            "user_evidence_source": item.user_evidence_source,
            "confidence": round(item.confidence, 2),
            "need_text": item.need_text,
        }
        for item in sorted(needs_by_id.values(), key=lambda value: (-REQUIREMENT_WEIGHTS[value.requirement_level], value.parameter_id))
    ]

    need_tags = sorted({item["parameter_id"].replace("_", " ") for item in needs if item["requirement_level"] in {"REQUIRED", "HIGH"}})
    priority_parameter_ids = [item["parameter_id"] for item in needs if item["requirement_level"] in {"REQUIRED", "HIGH"}]
    profile_key = "stroke" if any("stroke" in item["need_text"].lower() for item in needs) else ("memory" if any(item["parameter_id"] in {"memory_care", "dementia_alz_programs"} for item in needs) else None)

    return {
        "generated_from": {
            "questionnaire": True,
            "natural_language": bool((natural_language_query or "").strip()),
        },
        "needs": needs,
        "need_tags": need_tags,
        "priority_parameter_ids": priority_parameter_ids,
        "profile_key": profile_key,
        "location_city": nl_meta.get("location_city"),
        "natural_language_mapping": nl_meta,
    }


def _contains(text, *tokens):
    return any(token in text for token in tokens)

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
    if _contains(text, "both of us", "both parents", "husband and wife"):
        return True
    if re.search(r"\b(?:parents|partners|spouses)\s+are\s+both\b(?!\s+(?:deceased|dead)\b)", text):
        return True
    if re.search(r"\b(?:parents|partners|spouses)\b", text) and re.search(
        r"\b(?:they\s+)?(?:want|wish|plan)\s+to\s+(?:live|stay|move)\s+together\b", text
    ):
        return True
    if re.search(r"\bmy (?:husband|wife|spouse|partner) and i\b", text):
        return True
    if re.search(r"\b(?:parents|partners|spouses)\b[^.]{0,80}\b(?:together|same (?:community|home|room|unit)|remain together|remain near each other|stay near each other|live near each other)\b", text):
        return True
    return bool(re.search(r"\b(?:together|same (?:community|home|room|unit))\b[^.]{0,80}\b(?:parents|partners|spouses)\b", text))


def _duration_months(text: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*(?:month|months|mo)\b", text)
    if match:
        return int(match.group(1))
    if _contains(text, "three months", "3 months"):
        return 3
    return None



def _extract_strategy_facts(questionnaire_state, natural_language_query, *, care_denials):
    from app.services.living_strategy_runtime import _norm, _hi, _contains, _first_known
    from app.services.care_input_assertions import extract_care_denials
    denials = care_denials if care_denials is not None else extract_care_denials(natural_language_query)
    query = _norm(natural_language_query)
    hi = _hi(questionnaire_state)
    transition = hi.get("transitionRiskProfile") if isinstance(hi.get("transitionRiskProfile"), dict) else {}
    finance = hi.get("financialProfile") if isinstance(hi.get("financialProfile"), dict) else {}

    # `relationship` identifies who the search is for (for example, "my spouse");
    # it does not mean two residents are moving. Require an explicit joint-move or
    # co-residence statement before creating the COUPLE_CORESIDENCE hard gate.
    couple = _mentions_couple(query)

    no_dementia = denials["memory"] or _norm(questionnaire_state.get("memoryStatus")) in {"no", "none", "no dementia", "no memory concerns"}
    memory_care_needed = (
        not no_dementia
        and _contains(query, "dementia", "alzheimer", "memory care", "wandering", "cognitive decline", "cognitive impairment")
    ) or _norm(questionnaire_state.get("memoryStatus")) in {"yes", "dementia", "memory care", "alzheimer", "alzheimers"}

    surgery = _contains(query, "surgery", "operation", "post-op", "postoperative")
    spine_or_back = _contains(query, "spine", "spinal", "back surgery", "back operation")
    rehab = _contains(query, "rehab", "rehabilitation", "physical therapy", "physiotherapy", "pt ", " pt", "occupational therapy")
    # A phrase such as "not temporary" must not be mistaken for temporary recovery merely
    # because it contains the word "temporary". Persistent ADL support belongs on the
    # Assisted Living path, while a genuine recovery episode can lead with lower intensity.
    explicitly_persistent = _contains(
        query,
        "not temporary",
        "not a temporary",
        "permanent",
        "ongoing daily help",
        "ongoing help",
        "not expected to recover",
    )
    expected_recovery = not explicitly_persistent and _contains(
        query,
        "expected to walk",
        "should walk again",
        "return to walking",
        "expected to recover",
        "temporary",
        "short-term",
        "short term",
    )
    duration = _duration_months(query)
    if duration is not None and duration <= 6:
        expected_recovery = True

    explicit_independence = denials["independent"] or _contains(_norm(questionnaire_state.get("assistanceLevel")), "fully independent", "independent")
    no_adl_support = explicit_independence or denials["adl"]
    no_medication_support = (explicit_independence and _contains(query, "medication", "medications", "medicine")) or denials["medication"]
    # Keep explicit, ordinary-language ADL statements canonical even when the
    # client does not name a specific task.  The launch journeys exposed three
    # equivalent phrases ("assistance with daily activities", "substantial
    # daily assistance", and "light daily assistance") that were accounted for
    # as client statements but were not promoted into the strategy signal.  The
    # downstream MUST gate therefore silently lost ADL_SUPPORT_AVAILABLE.
    adl = (not no_adl_support) and (
        _contains(
            query,
            "bathing",
            "dressing",
            "shower",
            "toileting",
            "adl",
            "personal care",
            "daily assistance",
            "daily activities",
            "activities of daily living",
            "daily living assistance",
        )
        or _contains(_norm(questionnaire_state.get("assistanceLevel")), "bathing", "dressing", "assistance")
    )
    medication = (not no_medication_support) and _contains(query, "medication", "medications", "medicine")
    high_social = _contains(query, "culture", "cultural", "classes", "activities", "social", "clubs", "lectures", "music", "art", "events")

    raw_rehab_need = _norm(transition.get("postHospitalRehabNeed"))
    skilled_rehab_known = raw_rehab_need in {"yes", "required", "high"} or _contains(query, "physical therapy", "occupational therapy", "skilled rehab", "rehabilitation")

    move_timing = _norm(transition.get("moveTiming") or questionnaire_state.get("moveTiming"))
    budget = _first_known(questionnaire_state, "budget", "monthlyBudget")
    medicare = _norm(finance.get("medicareStatus") or questionnaire_state.get("medicareStatus"))
    entrance_fee = _norm(finance.get("entranceFeeTolerance") or questionnaire_state.get("entranceFeeTolerance"))

    return {"couple": couple, "no_dementia": no_dementia, "memory_care_needed": memory_care_needed, "surgery": surgery, "spine_or_back": spine_or_back, "rehab": rehab, "expected_recovery": expected_recovery, "duration": duration, "explicit_independence": explicit_independence, "no_adl_support": no_adl_support, "no_medication_support": no_medication_support, "adl": adl, "medication": medication, "high_social": high_social, "skilled_rehab_known": skilled_rehab_known, "move_timing": move_timing, "budget": budget, "medicare": medicare, "entrance_fee": entrance_fee}

def _extract_delivery_facts(questionnaire_state: Dict[str, Any], natural_language_query: str, *, care_denials=None) -> Dict[str, Any]:
    from app.services.care_input_assertions import extract_care_denials
    denials = care_denials if care_denials is not None else extract_care_denials(natural_language_query)
    text = str(natural_language_query or "").lower()
    assistance = str(questionnaire_state.get("assistanceLevel") or "").lower()
    combined = f"{text} {assistance}"
    temporary = any(token in combined for token in ("temporary", "temporarily", "3 months", "three months", "short term", "short-term", "post surgery", "after surgery", "recovery", "recovering"))
    home_like = any(token in combined for token in ("intimate", "home-like", "homelike", "home like", "small community", "less institutional", "not institutional", "independent living", "independent senior living"))
    part_time = any(token in combined for token in ("few hours", "a few hours", "couple hours", "part time", "part-time", "morning and evening", "morning/evening", "one hour", "1 hour"))
    meals_material = any(token in combined for token in ("meal", "meals", "food", "dining", "breakfast", "lunch", "dinner", "ארוחות", "אוכל"))
    in_house_only_requested = any(token in combined for token in (
        "everything in house", "everything in-house", "all in house", "all in-house",
        "only in house", "only in-house", "in house only", "in-house only",
        "no outside care", "no outside caregiver", "no external care", "no external agency",
        "no outside agency", "not okay with outside caregivers", "not comfortable with outside caregivers",
        "don't want outside caregivers", "do not want outside caregivers",
    ))
    return {
        "temporary_care_need": temporary,
        "home_like_or_independent_preference": home_like,
        "part_time_care_pattern": part_time,
        "meals_material": meals_material,
        "in_house_only_requested": in_house_only_requested,
    }


def _extract_preferences(questionnaire_state, natural_language_query):
    query = str(natural_language_query or "").lower()
    city = str(questionnaire_state.get("locationCity") or questionnaire_state.get("city") or "").strip().upper()
    # The product market is the Las Vegas Valley, not only the incorporated city.
    # Preserve a stated valley location such as Henderson as the canonical market
    # MUST instead of dropping location merely because the words "Las Vegas" were
    # not repeated in free text.
    las_vegas_valley_terms = (
        "las vegas",
        "henderson",
        "north las vegas",
        "summerlin",
        "clark county",
    )
    las_vegas_valley_cities = {
        "LAS VEGAS",
        "HENDERSON",
        "NORTH LAS VEGAS",
        "SUMMERLIN",
        "PARADISE",
        "SPRING VALLEY",
        "ENTERPRISE",
        "WINCHESTER",
        "SUNRISE MANOR",
    }
    las_vegas_requested = any(term in query for term in las_vegas_valley_terms) or city in las_vegas_valley_cities
    city_limits_only = any(token in query for token in ("las vegas city limits", "city limits only", "within las vegas city", "only in las vegas city"))
    human = questionnaire_state.get("humanIntelligenceV2") or {}
    food = human.get("foodProfile") or {}
    future = human.get("futureCareProfile") or {}
    dietary = " ".join(str(v).lower() for v in food.get("dietaryPreferences") or [])
    continuum = " ".join(str(v or "").lower() for v in (future.get("avoidFutureMovesPreference"), future.get("continuumOfCarePreference"), questionnaire_state.get("futureCarePreference")))
    return {
        "las_vegas_requested": las_vegas_requested, "city_limits_only": city_limits_only,
        "classical_music": any(t in query for t in ("classical music", "classical concert", "classical concerts")),
        "transportation": "transport" in query or "outings" in query,
        "dining": any(t in query for t in ("dining", "restaurant", "food")),
        "kosher": "kosher" in query or "kosher" in dietary,
        "continuum": any(t in query for t in ("continuum of care", "continuing care", "life plan", "ccrc")) or any(t in continuum for t in ("required", "preferred", "important", "continuum")),
        "care_search_approach": str(questionnaire_state.get("careSearchApproach") or "").strip().lower(),
    }

def _community_size_preference(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    raw = _nested(questionnaire, "humanIntelligenceV2", "personalityProfile", "communitySizePreference")
    normalized = _norm(raw)
    if not normalized:
        return {"value": "UNKNOWN", "source": "UNKNOWN", "confidence": 0.0}
    if any(token in normalized for token in ("small", "intimate", "few", "home-like", "home like")):
        return {"value": "SMALL", "source": "questionnaire.humanIntelligenceV2.personalityProfile.communitySizePreference", "confidence": 1.0}
    if any(token in normalized for token in ("large", "bigger", "many people", "active community", "large community")):
        return {"value": "LARGE", "source": "questionnaire.humanIntelligenceV2.personalityProfile.communitySizePreference", "confidence": 1.0}
    if "medium" in normalized or "mid" in normalized:
        return {"value": "MEDIUM", "source": "questionnaire.humanIntelligenceV2.personalityProfile.communitySizePreference", "confidence": 1.0}
    if "no preference" in normalized or "either" in normalized:
        return {"value": "NO_PREFERENCE", "source": "questionnaire.humanIntelligenceV2.personalityProfile.communitySizePreference", "confidence": 1.0}
    return {"value": "UNKNOWN", "source": "questionnaire.humanIntelligenceV2.personalityProfile.communitySizePreference", "confidence": 0.5, "raw": _text(raw)}


def _recent_bereavement(questionnaire: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    family = _nested(questionnaire, "humanIntelligenceV2", "familyProfile") or {}
    transition = _nested(questionnaire, "humanIntelligenceV2", "transitionRiskProfile") or {}
    candidates = [
        (family.get("widowStatus"), "questionnaire.humanIntelligenceV2.familyProfile.widowStatus"),
        (family.get("lossTiming"), "questionnaire.humanIntelligenceV2.familyProfile.lossTiming"),
        (transition.get("bereavementStatus"), "questionnaire.humanIntelligenceV2.transitionRiskProfile.bereavementStatus"),
    ]
    for value, source in candidates:
        if _contains_any(value, ("widow", "widower", "bereav", "recent loss", "recently", "spouse died", "spouse passed", "within 6 months", "6-12 months", "within 1 year")):
            return {"value": "YES", "source": source, "confidence": 1.0}
    nl = _norm(natural_language_query)
    if re.search(r"\b(recently\s+widow(?:ed|er)?|recent\s+bereavement|spouse\s+(?:died|passed)|wife\s+(?:died|passed)|husband\s+(?:died|passed))\b", nl):
        return {"value": "YES", "source": "natural_language", "confidence": 0.95}
    return {"value": "UNKNOWN", "source": "UNKNOWN", "confidence": 0.0}


def _social_transition_priority(questionnaire: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    hi = questionnaire.get("humanIntelligenceV2") if isinstance(questionnaire.get("humanIntelligenceV2"), dict) else {}
    family = hi.get("familyProfile") if isinstance(hi.get("familyProfile"), dict) else {}
    social = hi.get("socialProfile") if isinstance(hi.get("socialProfile"), dict) else {}
    transition = hi.get("transitionRiskProfile") if isinstance(hi.get("transitionRiskProfile"), dict) else {}
    explicit = [
        (family.get("socialInteractionNeed"), "questionnaire.humanIntelligenceV2.familyProfile.socialInteractionNeed"),
        (social.get("newFriendsImportance"), "questionnaire.humanIntelligenceV2.socialProfile.newFriendsImportance"),
        (social.get("preferredSocialIntensity"), "questionnaire.humanIntelligenceV2.socialProfile.preferredSocialIntensity"),
        (transition.get("lonelinessRisk"), "questionnaire.humanIntelligenceV2.transitionRiskProfile.lonelinessRisk"),
        (transition.get("socialIsolationConcern"), "questionnaire.humanIntelligenceV2.transitionRiskProfile.socialIsolationConcern"),
    ]
    for value, source in explicit:
        if _explicit_high(value):
            return {"value": "HIGH", "source": source, "confidence": 1.0}
    for value, source in explicit:
        if _explicit_low(value):
            return {"value": "LOW", "source": source, "confidence": 1.0}
    for value, source in explicit:
        if _explicit_neutral(value):
            return {"value": "NEUTRAL", "source": source, "confidence": 1.0}
    bereavement = _recent_bereavement(questionnaire, natural_language_query)
    if bereavement["value"] == "YES":
        return {
            "value": "REVIEW_REQUIRED",
            "source": bereavement["source"],
            "confidence": bereavement["confidence"],
            "reason": "Recent bereavement makes social and transition fit material but does not determine preferred social intensity.",
        }
    return {"value": "UNKNOWN", "source": "UNKNOWN", "confidence": 0.0}


def _independence_priority(questionnaire: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    profile = _nested(questionnaire, "humanIntelligenceV2", "independenceProfile") or {}
    values = [profile.get("drivingImportance"), profile.get("cookingImportance"), profile.get("abilityToLeaveIndependently"), profile.get("hostingFamilyImportance")]
    if any(_explicit_high(value) for value in values):
        return {"value": "HIGH", "source": "questionnaire.humanIntelligenceV2.independenceProfile", "confidence": 1.0}
    nl = _norm(natural_language_query)
    if any(token in nl for token in ("still independent", "independent", "still mobile", "drives himself", "drives herself", "mobile")):
        return {"value": "HIGH", "source": "natural_language", "confidence": 0.8}
    return {"value": "UNKNOWN", "source": "UNKNOWN", "confidence": 0.0}


def _transition_participation(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    transition = _nested(questionnaire, "humanIntelligenceV2", "transitionRiskProfile") or {}
    family_culture = _nested(questionnaire, "humanIntelligenceV2", "familyCultureProfile") or {}
    raw = transition.get("attitudeTowardMove")
    normalized = _norm(raw)
    if normalized:
        if any(
            token in normalized
            for token in (
                "positive",
                "involved",
                "his choice",
                "her choice",
                "ready",
                "wants to move",
                "want to move",
                "does not want to remain alone",
                "doesn't want to remain alone",
                "does not want to stay alone",
            )
        ):
            return {"value": "PARTICIPATING", "source": "questionnaire.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove", "confidence": 1.0}
        if any(token in normalized for token in ("cautious", "open", "uncertain")):
            return {"value": "CAUTIOUS", "source": "questionnaire.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove", "confidence": 1.0}
        if any(token in normalized for token in ("reluctant", "pushed", "forced", "against")):
            return {"value": "LOW_PARTICIPATION_RISK", "source": "questionnaire.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove", "confidence": 1.0}
        if any(token in normalized for token in ("not sure", "unsure")):
            return {"value": "ACKNOWLEDGED_UNKNOWN", "source": "questionnaire.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove", "confidence": 1.0}
    decision_role = _norm(family_culture.get("decisionRole"))
    if decision_role == "resident decides":
        return {"value": "PARTICIPATING", "source": "questionnaire.humanIntelligenceV2.familyCultureProfile.decisionRole", "confidence": 0.9}
    return {"value": "UNKNOWN", "source": "UNKNOWN", "confidence": 0.0}



def _has_need(profile: Dict[str, Any], parameter_id: str) -> bool:
    return any(str(item.get("parameter_id") or "") == parameter_id for item in profile.get("needs") or [])


def _append_need(profile: Dict[str, Any], parameter_id: str, level: str, text: str, source: str) -> None:
    if _has_need(profile, parameter_id):
        return
    profile.setdefault("needs", []).append({
        "parameter_id": parameter_id,
        "requirement_level": level,
        "desired_value": "YES",
        "acceptable_values": ["YES", "UNKNOWN"],
        "applicable_scope": "SERVICE",
        "user_evidence_source": source,
        "confidence": 0.9,
        "need_text": text,
    })


def _apply_strategy_needs(profile: Dict[str, Any], strategy: Dict[str, Any]) -> None:
    signals = strategy.get("signals") if isinstance(strategy.get("signals"), dict) else {}
    if signals.get("rehabilitation_need_detected"):
        _append_need(profile, "pt", "HIGH", "Physical therapy / post-operative rehabilitation support", "living_strategy_runtime")
        _append_need(profile, "ot", "MEDIUM", "Occupational therapy may be needed during recovery", "living_strategy_runtime")
    if signals.get("adl_support_needed"):
        _append_need(profile, "adl_support", "HIGH", "Temporary or ongoing help with activities of daily living", "living_strategy_runtime")
    if signals.get("medication_support_needed"):
        _append_need(profile, "medication_support", "HIGH", "Medication-management support", "living_strategy_runtime")



def extract_intake_facts(questionnaire_state, natural_language_query="", *, care_denials=None):
    from app.services.care_input_assertions import extract_care_denials
    from app.services.decision_engine_evidence import _explicit_location_city
    from app.services.living_strategy_guard_patch import deceased_spouse_without_current_couple
    state = deepcopy(questionnaire_state or {})
    story = str(natural_language_query or "")
    denials = care_denials if care_denials is not None else extract_care_denials(story)
    clinical = _extract_clinical_profile(state, story, care_denials=denials)
    if not clinical.get("location_city"):
        city = _explicit_location_city(state, story)
        if city:
            clinical["location_city"] = city
            clinical["natural_language_mapping"]["location_city"] = city
            clinical["natural_language_mapping"]["extraction"]["recognized_tokens"].append(city.lower())
    strategy = _extract_strategy_facts(state, story, care_denials=denials)
    _apply_strategy_needs(clinical, {"signals": {
        "rehabilitation_need_detected": strategy["rehab"] or strategy["surgery"],
        "adl_support_needed": strategy["adl"],
        "medication_support_needed": strategy["medication"],
    }})
    # One positive requirement owns each shared care fact. These are projections
    # of explicit clinical requirements, never a second reading of the story.
    positive = {
        n["parameter_id"] for n in clinical["needs"]
        if n["desired_value"] == "YES"
        # The legacy structured nursing mapping carries possible transfer/
        # medication support at <1 confidence. That is derived care context,
        # not an explicit client statement and must not create a new MUST.
        and not (n["user_evidence_source"] == "questionnaire.assistanceLevel" and n["confidence"] < 1.0)
    }
    strategy["adl"] = "adl_support" in positive
    strategy["medication"] = "medication_support" in positive
    delivery = _extract_delivery_facts(state, story, care_denials=denials)
    delivery["adl_support_needed"] = strategy["adl"]
    delivery["medication_support_needed"] = strategy["medication"]
    delivery["external_care_strategy_material"] = strategy["adl"] and any(delivery[k] for k in ("temporary_care_need", "home_like_or_independent_preference", "part_time_care_pattern"))
    combined = (story + " " + str(state.get("assistanceLevel") or "")).lower()
    return {
        "schema_version": "intake-facts-v1",
        "source_digest": _digest({"state": state, "story": story}),
        "questionnaire_state": state,
        "clinical_profile": clinical,
        "denials": dict(denials),
        "strategy": strategy,
        "delivery": delivery,
        "preferences": _extract_preferences(state, story),
        "deceased_spouse_without_current_couple": deceased_spouse_without_current_couple(state, story),
        "care_tasks": {
            "bathing": any(t in combined for t in ("bath", "shower")),
            "dressing": any(t in combined for t in ("dress", "socks", "shoes")),
            "transfer": any(t in combined for t in ("transfer", "mobility", "walker", "wheelchair")),
        },
        "human": {
            "community_size_preference": _community_size_preference(state),
            "recent_bereavement": _recent_bereavement(state, story),
            "social_transition_priority": _social_transition_priority(state, story),
            "independence_priority": _independence_priority(state, story),
            "decision_participation": _transition_participation(state),
        },
    }

def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def seal_interpretation(profile, facts):
    """Bind the exact interpreted facts and validated model output to the profile.

    Consumers cannot silently substitute another needs/strategy/intent projection.
    The digest contains no client identifiers and is safe to compare across stages.
    """
    record = deepcopy(facts)
    record["clinical_profile"] = {k: deepcopy(profile[k]) for k in ("needs", "need_tags", "priority_parameter_ids", "profile_key", "location_city")}
    human = (profile.get("decision_intelligence") or {}).get("human_intelligence") or {}
    record["semantic_validation"] = deepcopy(human.get("semantic_ai") or {})
    record["living_strategy"] = deepcopy(profile.get("living_strategy"))
    record["client_intent"] = deepcopy(profile.get("client_intent"))
    record["care_delivery_signals"] = deepcopy(profile.get("care_delivery_signals"))
    record["care_partner_requirements"] = deepcopy(profile.get("care_partner_requirements"))
    profile["intake_interpretation"] = record
    profile["interpretation_id"] = _digest(record)

def validate_interpretation(profile):
    record = profile.get("intake_interpretation")
    if record is None:  # historical stored profiles remain readable until expiry
        return
    if profile.get("interpretation_id") != _digest(record):
        raise ValueError("INTAKE_INTERPRETATION_INTEGRITY_MISMATCH")
    for key, value in record["clinical_profile"].items():
        if profile.get(key) != value:
            raise ValueError("INTAKE_INTERPRETATION_PROJECTION_CHANGED:" + key)
    for key in ("living_strategy", "client_intent", "care_delivery_signals", "care_partner_requirements"):
        if profile.get(key) != record.get(key):
            raise ValueError("INTAKE_INTERPRETATION_PROJECTION_CHANGED:" + key)
