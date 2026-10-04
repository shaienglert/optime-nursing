from __future__ import annotations

"""Client-intent gate and governed post-gate ranking semantics.

Decision order:
1. Understand what the client actually wants.
2. Reject only VERIFIED MUST mismatches. UNKNOWN never becomes a mismatch; a
   material MUST unknown keeps the decision provisional and should be researched/asked.
3. Rank surviving candidates by explicit NICE-TO-HAVE fit.
4. Then use objective evidence: government/regulatory quality, public reputation,
   and relevant evidence completeness.

No arbitrary numeric quality weights are introduced here; ordering is lexicographic
and auditable. Numeric values are used only where an explicit user-preference fit
already has a governed score (for example community-environment congruence).
"""

import re
from typing import Any, Dict, List

from app.services import governed_evidence_runtime
from app.services.public_reputation_runtime import get_public_reputation


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


URGENT_MOVE_TIMINGS = {"immediately", "within 30 days"}
URGENT_AVAILABILITY_KEY = "CURRENT_AVAILABILITY_FOR_URGENT_MOVE"


_NEUTRAL_SELECTIONS = {
    "NO", "NONE", "NO PREFERENCE", "NO_PREFERENCE", "NOT IMPORTANT",
    "NOT REQUIRED", "NOT NEEDED", "NOT SURE", "UNKNOWN",
}
_REQUIRED_SELECTIONS = {"REQUIRED", "REQUIREMENT", "MUST", "MUST HAVE"}
_PREFERRED_SELECTIONS = {"PREFERRED", "PREFERENCE", "IMPORTANT", "VERY IMPORTANT", "NICE TO HAVE"}


def _selection(value: Any) -> str:
    """Compare questionnaire choices as complete values, never text fragments."""
    return str(value or "").strip().upper()


def build_client_intent(questionnaire_state: Dict[str, Any], natural_language_query: str, living_strategy: Dict[str, Any], human_context: Dict[str, Any], *, care_delivery_signals=None) -> Dict[str, Any]:
    query = str(natural_language_query or "").lower()
    signals = living_strategy.get("signals") if isinstance(living_strategy.get("signals"), dict) else {}
    household = living_strategy.get("household") if isinstance(living_strategy.get("household"), dict) else {}
    human_signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}

    must: List[Dict[str, Any]] = []
    nice: List[Dict[str, Any]] = []

    def add_must(key: str, reason: str, verification: str) -> None:
        must.append({"key": key, "reason": reason, "verification": verification})

    def add_nice(key: str, reason: str) -> None:
        if not any(str(item.get("key") or "") == key for item in nice):
            nice.append({"key": key, "reason": reason})

    # Unconditional, unlike every other MUST here: license validity matters regardless
    # of what the client asked for. Safe to always include because evaluate_candidate_intent
    # only fails this on a confirmed-past expiration_date (a curated registry field), never
    # on missing data -- so a row with no expiration_date recorded still passes.
    add_must("LICENSE_CURRENTLY_VALID", "A facility must hold a currently valid license; one whose license has expired should never be presented as a safe option.", "canonical license expiration_date vs current date")

    if care_delivery_signals is None:
        from app.services.combined_care_solution_runtime import _query_signals
        care_delivery_signals = _query_signals({}, natural_language_query)
    in_house_only_requested = bool(care_delivery_signals.get("in_house_only_requested"))

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
    if las_vegas_requested:
        if city_limits_only:
            add_must("LAS_VEGAS_CITY_LIMITS", "The client explicitly restricted the search to Las Vegas city limits.", "canonical city/state")
        else:
            add_must("LAS_VEGAS", "The requested market is the Las Vegas Valley/metro area unless the client explicitly narrows to city limits.", "canonical Las Vegas Valley market geography")

    if household.get("type") == "COUPLE":
        add_must("COUPLE_CORESIDENCE", "The couple wants to live together; a solution that cannot house both partners is not acceptable.", "unit/occupancy policy")

    if signals.get("adl_support_needed"):
        add_must("ADL_SUPPORT_AVAILABLE", "The resident explicitly needs bathing/dressing or other ADL assistance.", "service evidence or permitted outside-care model")

    if signals.get("medication_support_needed"):
        add_must("MEDICATION_SUPPORT_AVAILABLE", "The resident explicitly needs medication-management support; a facility cannot be called eligible until this capability is verified.", "verified medication-support evidence")

    # Two separate requirements. A memory need requires a setting that is officially
    # classified as memory care (this MUST). A secured/locked unit is a different, narrower
    # requirement that exists only for a confirmed wandering/security need (SECURED_UNIT_AVAILABLE).
    if signals.get("memory_care_needed"):
        add_must(
            "MEMORY_CARE_SETTING_CONFIRMED",
            "The resident has a memory-care need and requires an officially confirmed memory-care setting; ordinary assisted or independent living is not sufficient.",
            "Nevada official-detail memory-care classification",
        )

    human = questionnaire_state.get("humanIntelligenceV2") or {}
    future = human.get("futureCareProfile") or {}
    transition = human.get("transitionRiskProfile") or {}
    if signals.get("secure_memory_required") or _upper(future.get("secureMemoryNeighborhoodNeed")) == "YES" or _upper(transition.get("wanderingConcerns")) == "YES":
        add_must("SECURED_UNIT_AVAILABLE", "The resident explicitly needs a secure setting or wandering protection.", "verified secured-unit capability")

    if _upper(transition.get("postHospitalRehabNeed")) == "YES":
        add_must("POST_HOSPITAL_REHAB_PROGRAM", "Recovery after hospitalization requires a verified rehabilitation program with PT/OT, nursing and physician coordination.", "verified rehabilitation program and clinical support")

    if signals.get("rehabilitation_need_detected"):
        add_must("REHAB_PATH_AVAILABLE", "The recovery plan requires access to appropriate rehabilitation/PT/OT, either onsite or through a verified external pathway.", "rehab/PT/OT evidence")

    if signals.get("expected_recovery"):
        add_must("RECOVERY_TRANSITION_COMPATIBLE", "The solution must remain appropriate as temporary care needs decrease after recovery.", "care transition / outside-care / continuum policy")

    refuses_locked_memory_unit = bool(re.search(
        r"\b(?:not|no|without)\s+(?:a\s+)?(?:locked|secure)\s+memory(?:[- ]care)?\b",
        query,
    ))
    if signals.get("no_dementia"):
        add_must("NO_FORCED_MEMORY_PLACEMENT", "A cognitively intact resident should not be placed in a locked memory-care-only setting.", "care setting classification")
    elif refuses_locked_memory_unit:
        add_must("NO_FORCED_MEMORY_PLACEMENT", "A resident who does not need or explicitly declines a locked memory-care-only setting should not be placed there.", "care setting classification")

    if signals.get("high_social_culture_priority"):
        add_nice("RICH_CULTURE_AND_ACTIVITIES", "The clients explicitly want substantial culture, classes, events and social opportunities.")
    if any(token in query for token in ("classical music", "classical concert", "classical concerts")):
        add_nice("CLASSICAL_MUSIC_ACCESS", "The client explicitly values classical music; generic social programming is not sufficient evidence for this preference.")

    community = human_signals.get("community_size_preference") if isinstance(human_signals.get("community_size_preference"), dict) else {}
    community_value = _upper(community.get("value"))
    if community_value not in _NEUTRAL_SELECTIONS:
        add_nice("COMMUNITY_ENVIRONMENT_MATCH", "The client expressed a community-size/environment preference.")

    if "transport" in query or "outings" in query:
        add_nice("TRANSPORTATION_AND_OUTINGS", "Transportation/outings are part of the desired lifestyle.")
    if any(token in query for token in ("dining", "restaurant", "food")):
        add_nice("DINING_EXPERIENCE", "Dining quality/experience is explicitly relevant.")
    human_profile = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    # A stated preferred language is a NICE the Structured Profile carries; it used to be
    # dropped before ranking (golden ranking oracle, persona 007).
    language_profile = human_profile.get("languageProfile") if isinstance(human_profile.get("languageProfile"), dict) else {}
    preferred_language = str(language_profile.get("preferredSpokenLanguage") or language_profile.get("medicalDiscussionLanguage") or "").strip()
    language_scope = _selection(language_profile.get("languageNeedScope"))
    # "Other" names no language: it cannot be matched against a facility language list, so it
    # would only create a false mismatch (or, as a requirement, exclude every community).
    if preferred_language and _selection(preferred_language) not in _NEUTRAL_SELECTIONS | {"ENGLISH", "OTHER"} and language_scope not in _NEUTRAL_SELECTIONS:
        language_required = language_scope in _REQUIRED_SELECTIONS
        if language_required:
            add_must("REQUIRED_LANGUAGE_SUPPORT", f"The resident explicitly requires {preferred_language} language support.", "verified language capability")
            must[-1]["value"] = preferred_language
        else:
            add_nice("PREFERRED_LANGUAGE_SUPPORT", f"The resident prefers {preferred_language}; verified language support should rank higher.")
            nice[-1]["value"] = preferred_language
    pending_clarification: List[Dict[str, Any]] = []
    if preferred_language and _selection(preferred_language) == "OTHER" and language_scope in _REQUIRED_SELECTIONS:
        # The family marked a language as required but did not name it. The requirement is
        # kept (not dropped, not matched against "Other") until the language is clarified.
        pending_clarification.append({
            "key": "REQUIRED_LANGUAGE_SUPPORT",
            "status": "PENDING_CLARIFICATION",
            "question_key": "required_language",
            "question": "Which language is required?",
            "reason": "A required language was marked as Other without naming it.",
        })
    social_profile = human_profile.get("socialProfile") if isinstance(human_profile.get("socialProfile"), dict) else {}
    social_frequency = str(social_profile.get("socialInteractionFrequency") or "").strip()
    if social_frequency and _selection(social_frequency) not in _NEUTRAL_SELECTIONS:
        # The stated pace of social life (from "Very little" to "Daily") is a preference to
        # check against relevant evidence. No verified evidence of a community's social pace
        # exists, so it stays UNKNOWN -- visible, never a match or a mismatch by default.
        add_nice("SOCIAL_FREQUENCY_MATCH", f"The client prefers a social pace of '{social_frequency}'; this stays unverified until relevant evidence exists.")
        nice[-1]["value"] = social_frequency
    activities = [str(x).strip() for x in social_profile.get("hobbyParticipation") or [] if str(x).strip() and _selection(x) not in _NEUTRAL_SELECTIONS]
    if activities and _selection(social_profile.get("activityRequirementLevel")) in _REQUIRED_SELECTIONS:
        add_must("REQUIRED_ACTIVITIES", "The family explicitly marked the selected activities as required.", "verified activities/programming evidence")
        must[-1]["value"] = activities
    food_profile = human_profile.get("foodProfile") if isinstance(human_profile.get("foodProfile"), dict) else {}
    dietary_preferences = {_selection(value) for value in food_profile.get("dietaryPreferences") or []}
    cultural_profile = human_profile.get("culturalProfile") if isinstance(human_profile.get("culturalProfile"), dict) else {}
    kosher_level = _selection(cultural_profile.get("kosherRequirements"))
    if kosher_level not in _NEUTRAL_SELECTIONS and ("kosher" in query or "KOSHER" in dietary_preferences):
        if kosher_level in _REQUIRED_SELECTIONS:
            add_must("KOSHER_MEALS", "The client explicitly marked keeping kosher as a requirement.", "verified kosher meal capability")
        else:
            add_nice("KOSHER_MEALS", "Verified kosher meal availability is an explicit resident preference.")

    budget = questionnaire_state.get("budget")
    if isinstance(budget, (int, float)) and float(budget) > 0:
        add_nice("BUDGET_FIT", "The verified starting monthly price should fit the client's stated budget.")

    # Availability depends on move timing (owner, 2026-10-02). For an urgent move it is a
    # CLIENT MUST: only current YES/LIMITED evidence passes; a recorded NO is
    # PENDING_RECONFIRMATION (volatile, never a permanent fail) and no/stale evidence is
    # EVIDENCE_PENDING -- neither is shown as a recommendation now. For a later move it is
    # informational and never excludes a community.
    move_timing = str(questionnaire_state.get("moveTiming") or "").strip()
    if move_timing.lower() in URGENT_MOVE_TIMINGS:
        add_must(URGENT_AVAILABILITY_KEY, f"The family needs to move {move_timing.lower()}; current availability must be confirmed.", "current availability YES/LIMITED from governed evidence or direct confirmation")
    if move_timing and move_timing.lower() not in {"not sure", "planning ahead"}:
        # Owner decision (2026-10-04): availability is never required beyond the urgent-move
        # MUST above. A community that publishes vacancies is relevant; FULL (YES) ranks above
        # LIMITED, and a recorded NO ranks lowest without excluding a later move.
        add_nice("AVAILABILITY_FIT", "A community that publishes current vacancies is more relevant; full availability ranks above limited.")

    future_profile = human_profile.get("futureCareProfile") if isinstance(human_profile.get("futureCareProfile"), dict) else {}
    continuum_selections = {
        _selection(value)
        for value in (
            future_profile.get("avoidFutureMovesPreference"),
            future_profile.get("continuumOfCarePreference"),
            questionnaire_state.get("futureCarePreference"),
        ) if _selection(value)
    }
    if continuum_selections & _REQUIRED_SELECTIONS:
        add_must("CONTINUUM_OF_CARE_REQUIRED", "The client marked future care continuity as required.", "verified life-plan care continuum")
    elif (
        continuum_selections & _PREFERRED_SELECTIONS
        or "FULL CONTINUUM OF CARE ON ONE CAMPUS" in continuum_selections
        or (not continuum_selections and any(token in query for token in ("continuum of care", "continuing care", "life plan", "ccrc")))
    ):
        add_nice("CONTINUUM_OF_CARE", "The client wants future care levels available without another move.")

    # Record sources at the deterministic consumer, separately from semantic
    # interpretation and actual comparator effects. Only active intent keys are
    # linked; arbitrary narrative mentions cannot credit a questionnaire answer.
    source_links = []
    from app.services.questionnaire_answer_accounting import _at
    source_paths = {
        "BUDGET_FIT": ("budget",),
        "SOCIAL_FREQUENCY_MATCH": ("humanIntelligenceV2.socialProfile.socialInteractionFrequency",),
        "REQUIRED_ACTIVITIES": ("humanIntelligenceV2.socialProfile.hobbyParticipation", "humanIntelligenceV2.socialProfile.activityRequirementLevel"),
        "PREFERRED_LANGUAGE_SUPPORT": ("humanIntelligenceV2.languageProfile.preferredLanguage", "humanIntelligenceV2.languageProfile.medicalDiscussionLanguage", "humanIntelligenceV2.languageProfile.languageNeedScope"),
        "REQUIRED_LANGUAGE_SUPPORT": ("humanIntelligenceV2.languageProfile.preferredLanguage", "humanIntelligenceV2.languageProfile.medicalDiscussionLanguage", "humanIntelligenceV2.languageProfile.languageNeedScope"),
        "CONTINUUM_OF_CARE": ("futureCarePreference", "humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference", "humanIntelligenceV2.futureCareProfile.continuumOfCarePreference"),
        "CONTINUUM_OF_CARE_REQUIRED": ("futureCarePreference", "humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference", "humanIntelligenceV2.futureCareProfile.continuumOfCarePreference"),
    }
    for item in must + nice:
        for path in source_paths.get(item["key"], ()):
            value = _at(questionnaire_state, path)
            values = list(enumerate(value)) if isinstance(value, list) else [(None, value)]
            for index, answer in values:
                if answer is None or answer == "" or _selection(answer) in _NEUTRAL_SELECTIONS:
                    continue
                if item["key"].startswith("CONTINUUM_OF_CARE") and _selection(answer) not in (_REQUIRED_SELECTIONS | _PREFERRED_SELECTIONS | {"FULL CONTINUUM OF CARE ON ONE CAMPUS"}):
                    continue
                # The fallback language field is read only without a preferred language.
                if path.endswith("medicalDiscussionLanguage") and language_profile.get("preferredLanguage"):
                    continue
                source_links.append({"answer_path": path, "selection_index": index,
                                     "answer": answer, "intent_key": item["key"]})
    result = {
        "version": "client-intent-runtime-v1.6",
        "answer_source_links": source_links,
        "unrecognized_controls": [
            {"answer_path": path, "answer": value, "status": "UNRECOGNIZED_CONTROL_VALUE"}
            for path, value in (
                ("futureCarePreference", questionnaire_state.get("futureCarePreference")),
                ("humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference", future_profile.get("avoidFutureMovesPreference")),
                ("humanIntelligenceV2.futureCareProfile.continuumOfCarePreference", future_profile.get("continuumOfCarePreference")),
            ) if _selection(value) and _selection(value) not in
            (_NEUTRAL_SELECTIONS | _REQUIRED_SELECTIONS | _PREFERRED_SELECTIONS | {"FULL CONTINUUM OF CARE ON ONE CAMPUS"})
        ],
        "must_haves": must,
        "nice_to_haves": nice,
        "in_house_only_requested": in_house_only_requested,
        "rule": "Client intent first -> verified MUST gate -> NICE-TO-HAVE MATCH/UNKNOWN/MISMATCH ordering -> objective government/regulatory evidence -> public reputation -> relevant evidence completeness.",
        "unknown_policy": "A material MUST with UNKNOWN evidence is not a pass or a fail; it triggers clarification or research and prevents finality. A specific NICE preference remains unresolved until evidence verifies that exact preference; known poor fit is MISMATCH, not UNKNOWN, and a broader category cannot silently satisfy it.",
        "external_care_policy": "A care-delivery MUST (e.g. medication management, ADL support) is satisfied by a verified in-house capability or a verified external-agency pathway as a complementary product; it is not restricted to in-house delivery unless the client explicitly asked for in-house-only care. External-vs-in-house delivery affects ranking and must be disclosed to the user, never used to silently exclude a facility.",
    }
    # Additive only when present, so intents without a pending requirement are unchanged.
    if pending_clarification:
        result["pending_clarification_requirements"] = pending_clarification
    return result


def evaluate_candidate_intent(row: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    hard_fail: List[str] = []
    must_unknown: List[str] = []
    pending_reasons: Dict[str, str] = {}
    must_pass: List[str] = []
    nice_match: List[str] = []
    nice_unknown: List[str] = []
    nice_mismatch: List[str] = []
    nice_fit_scores: Dict[str, float] = {}

    city = str(row.get("city") or "").strip().upper()
    state = str(row.get("state") or "").strip().upper()
    canonical_type = _upper(row.get("canonical_type"))
    person = row.get("human_person_fit") if isinstance(row.get("human_person_fit"), dict) else {}
    size = person.get("community_size") if isinstance(person.get("community_size"), dict) else {}
    payloads = governed_evidence_runtime.agent_and_provider_payloads(row)
    modalities = {_upper(value) for value in row.get("housing_modalities") or []}

    for must in intent.get("must_haves") or []:
        key = str(must.get("key") or "")
        if key == "LICENSE_CURRENTLY_VALID":
            # One authority: license_standing (also used by the market listing filter).
            # Where a license is legally required, missing/unverified is PENDING, never PASS.
            from app.services.license_standing import license_standing, VERIFIED_CURRENT, NOT_REQUIRED, EXPIRED, NOT_ACTIVE
            standing = row.get("license_standing") or license_standing(row)
            if standing in {VERIFIED_CURRENT, NOT_REQUIRED}:
                must_pass.append(key)
            elif standing in {EXPIRED, NOT_ACTIVE}:
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "LAS_VEGAS":
            las_vegas_valley_cities = {
                "LAS VEGAS", "HENDERSON", "NORTH LAS VEGAS", "PARADISE",
                "SPRING VALLEY", "ENTERPRISE", "WINCHESTER", "SUNRISE MANOR",
            }
            if state == "NV" and city in las_vegas_valley_cities:
                must_pass.append(key)
            else:
                hard_fail.append(key)
        elif key == "LAS_VEGAS_CITY_LIMITS":
            if state == "NV" and city == "LAS VEGAS":
                must_pass.append(key)
            else:
                hard_fail.append(key)
        elif key == "NO_FORCED_MEMORY_PLACEMENT":
            synthetic_archetype = _upper(row.get("synthetic_archetype"))
            if canonical_type in {"MEMORY_CARE_ONLY", "LOCKED_MEMORY_CARE_ONLY"} or synthetic_archetype == "MEMORY_CARE":
                hard_fail.append(key)
            else:
                must_pass.append(key)
        elif key == "REQUIRED_LANGUAGE_SUPPORT":
            wanted = str(must.get("value") or "").strip().lower()
            verified = str((row.get("verified_capabilities") or {}).get("languages") or "").lower()
            if not verified or verified == "unknown":
                must_unknown.append(key)
            elif wanted and wanted in verified:
                must_pass.append(key)
            else:
                hard_fail.append(key)
        elif key == "REQUIRED_ACTIVITIES":
            wanted = [str(x).strip().lower() for x in must.get("value") or [] if str(x).strip()]
            verified = str((row.get("verified_capabilities") or {}).get("activities") or "").lower()
            if not verified or verified == "unknown":
                must_unknown.append(key)
            elif all(x in verified for x in wanted):
                must_pass.append(key)
            else:
                hard_fail.append(key)
        elif key == URGENT_AVAILABILITY_KEY:
            recorded = _upper((row.get("verified_capabilities") or {}).get("current_availability"))
            if recorded in {"YES", "LIMITED"}:
                must_pass.append(key)
            else:
                must_unknown.append(key)
                pending_reasons[key] = "PENDING_RECONFIRMATION" if recorded == "NO" else "EVIDENCE_PENDING"
        elif key == "KOSHER_MEALS":
            # Same evidence authority as the needs engine and the NICE branch below: the
            # governed kosher parameter. Verified YES passes, verified incompatible evidence
            # fails, and UNKNOWN stays a verification item.
            matched = {str(item.get("parameter_id") or "") for item in row.get("matched_needs") or []}
            gaps = {str(item.get("parameter_id") or "") for item in row.get("unmet_verified_needs") or []}
            if "kosher" in matched:
                must_pass.append(key)
            elif "kosher" in gaps:
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "MEDICAID_PATHWAY_REQUIRED":
            # Added by the affordability-floor rule (affordability_floor.py). Passes only on
            # verified Medicaid acceptance. UNKNOWN is a verification item, never a pass; and
            # since the research pipeline stores "not found" and "not researched" alike, an
            # unverified False never fails a community either.
            # Governed facility parameter first (verified YES/NO is real evidence either
            # way); then agent payloads, which may confirm but never exclude.
            governed = _upper((row.get("verified_capabilities") or {}).get("medicaid_attributes"))
            if governed == "YES" or any(p.get("medicaid_accepted_verified") is True for p in payloads):
                must_pass.append(key)
            elif governed == "NO":
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "ADL_SUPPORT_AVAILABLE":
            # Never hard-fail entry on unverified agent evidence -- see MEDICATION_SUPPORT_AVAILABLE
            # above for why: the research pipeline cannot currently distinguish "confirmed not
            # offered" from "never researched" (both are stored as False).
            # SKILLED_NURSING is included for the same reason ASSISTED_LIVING_RFG already is
            # (see REHAB_PATH_AVAILABLE below, which already treats it as auto-pass): ADL
            # assistance is a baseline requirement of that license category, not something a
            # facility could hold the license without providing. Before this, every skilled
            # nursing facility sat in MUST_PENDING_VERIFICATION on this key alone, even ones
            # with governed CMS-sourced evidence (facility_parameter_service.py) confirming
            # adl_support=YES that this gate simply never consulted.
            governed = _upper((row.get("verified_capabilities") or {}).get("adl_support"))
            if canonical_type in {"ASSISTED_LIVING_RFG", "SKILLED_NURSING"} or governed == "YES" or any(
                p.get("adl_support_verified") is True or p.get("outside_care_allowed_verified") is True
                for p in payloads
            ):
                must_pass.append(key)
            else:
                # A verified in-house NO is still not a fail: external_care_policy lets a
                # verified agency pathway satisfy the care need (combined care layer).
                must_unknown.append(key)
        elif key == "MEDICATION_SUPPORT_AVAILABLE":
            # Entry into the candidate list must never turn on an unverified "False": the
            # research pipeline currently cannot distinguish "confirmed not offered" from
            # "never researched" (both are stored as False), so a hard_fail here would wrongly
            # exclude facilities with no real negative finding. In-house-vs-external-agency
            # delivery is a ranking signal (see combined_care_solution_runtime.py), never a gate.
            governed = _upper((row.get("verified_capabilities") or {}).get("medication_support"))
            if governed == "YES" or any(p.get("medication_support_verified") is True for p in payloads):
                must_pass.append(key)
            else:
                must_unknown.append(key)
        elif key == "MEMORY_CARE_SETTING_CONFIRMED":
            if str(row.get("memory_care_classification") or "").strip().upper() == "CONFIRMED":
                must_pass.append(key)
            else:
                must_unknown.append(key)
        elif key == "SECURED_UNIT_AVAILABLE":
            secured = row.get("secured_unit_evidence") or {}
            if _upper(secured.get("value")) == "YES" and secured.get("verified") is True:
                must_pass.append(key)
            elif _upper(secured.get("value")) == "NO" and secured.get("verified") is True:
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "POST_HOSPITAL_REHAB_PROGRAM":
            proof = governed_evidence_runtime.post_hospital_rehab_state(row)
            if proof == "PASS":
                must_pass.append(key)
            elif proof == "FAIL":
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "REHAB_PATH_AVAILABLE":
            # Never hard-fail entry on unverified agent evidence -- see MEDICATION_SUPPORT_AVAILABLE.
            if canonical_type == "SKILLED_NURSING" or any(
                p.get("rehab_verified") is True
                or p.get("pt_ot_verified") is True
                or p.get("pt_ot_external_path_verified") is True
                for p in payloads
            ):
                must_pass.append(key)
            else:
                must_unknown.append(key)
        elif key == "COUPLE_CORESIDENCE":
            # Synthetic pilot policy is governed catalog evidence; absent real-world
            # evidence remains UNKNOWN, and explicit refusal is a verified failure.
            accepts_couples = row.get("accepts_couples") if row.get("synthetic_pilot") is True else None
            if accepts_couples is True or any(
                p.get("couple_coresidence_verified") is True
                or p.get("same_apartment_transition_verified") is True
                for p in payloads
            ):
                must_pass.append(key)
            elif accepts_couples is False:
                hard_fail.append(key)
            else:
                must_unknown.append(key)
        elif key == "RECOVERY_TRANSITION_COMPATIBLE":
            # Never hard-fail entry on unverified agent evidence -- see MEDICATION_SUPPORT_AVAILABLE.
            if "LIFE_PLAN_CCRC" in modalities or any(
                p.get("outside_care_allowed_verified") is True
                or p.get("continuum_of_care_verified") is True
                or p.get("same_apartment_transition_verified") is True
                for p in payloads
            ):
                must_pass.append(key)
            else:
                must_unknown.append(key)
        elif key == "CONTINUUM_OF_CARE_REQUIRED":
            # The governed pilot catalog explicitly classifies continuing-care
            # communities. Real facilities need a life-plan modality or curated
            # provider evidence; an unknown capability is never assumed to pass.
            synthetic_continuum = row.get("synthetic_pilot") is True and _upper(row.get("synthetic_archetype")) == "CONTINUING_CARE"
            provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
            evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else {}
            if synthetic_continuum or "LIFE_PLAN_CCRC" in modalities or evidence.get("continuum_of_care_verified") is True:
                must_pass.append(key)
            else:
                must_unknown.append(key)
        else:
            must_unknown.append(key)

    for nice in intent.get("nice_to_haves") or []:
        key = str(nice.get("key") or "")
        if key == "RICH_CULTURE_AND_ACTIVITIES":
            if any(p.get("social_engagement_verified") is True for p in payloads):
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            else:
                nice_unknown.append(key)
        elif key == "CLASSICAL_MUSIC_ACCESS":
            if any(p.get("classical_music_verified") is True for p in payloads):
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            else:
                nice_unknown.append(key)
        elif key == "COMMUNITY_ENVIRONMENT_MATCH":
            value = size.get("fit_score")
            if isinstance(value, (int, float)):
                score = float(value)
                nice_fit_scores[key] = score
                if score >= 70.0:
                    nice_match.append(key)
                else:
                    nice_mismatch.append(key)
            else:
                nice_unknown.append(key)
        elif key == "SOCIAL_FREQUENCY_MATCH":
            # No verified social-pace evidence exists: missing evidence is uncertainty, not a mismatch.
            nice_unknown.append(key)
        elif key == "TRANSPORTATION_AND_OUTINGS":
            if any(p.get("transportation_verified") is True for p in payloads):
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            else:
                nice_unknown.append(key)
        elif key == "PREFERRED_LANGUAGE_SUPPORT":
            wanted = str(nice.get("value") or "").strip().lower()
            verified = str((row.get("verified_capabilities") or {}).get("languages") or "").lower()
            if wanted and verified and verified != "unknown":
                if wanted in verified:
                    nice_match.append(key)
                    nice_fit_scores[key] = 100.0
                else:
                    nice_mismatch.append(key)
                    nice_fit_scores[key] = 0.0
            else:
                nice_unknown.append(key)
        elif key == "DINING_EXPERIENCE":
            if any(p.get("dining_verified") is True for p in payloads):
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            else:
                nice_unknown.append(key)
        elif key == "KOSHER_MEALS":
            matched = {str(item.get("parameter_id") or "") for item in row.get("matched_needs") or []}
            gaps = {str(item.get("parameter_id") or "") for item in row.get("unmet_verified_needs") or []}
            if "kosher" in matched:
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            elif "kosher" in gaps:
                nice_mismatch.append(key)
                nice_fit_scores[key] = 0.0
            else:
                nice_unknown.append(key)
        elif key == "AVAILABILITY_FIT":
            recorded = _upper((row.get("verified_capabilities") or {}).get("current_availability"))
            if recorded == "YES":
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            elif recorded == "LIMITED":
                nice_match.append(key)
                nice_fit_scores[key] = 50.0
            elif recorded == "NO":
                nice_mismatch.append(key)
                nice_fit_scores[key] = 0.0
            else:
                nice_unknown.append(key)
        elif key == "BUDGET_FIT":
            parameter_id = "current_price"
            matched = {str(item.get("parameter_id") or "") for item in row.get("matched_needs") or []}
            gaps = {str(item.get("parameter_id") or "") for item in row.get("unmet_verified_needs") or []}
            if parameter_id in matched:
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            elif parameter_id in gaps:
                nice_mismatch.append(key)
                nice_fit_scores[key] = 0.0
            else:
                nice_unknown.append(key)
        elif key == "CONTINUUM_OF_CARE":
            synthetic_archetype = _upper(row.get("synthetic_archetype"))
            if "LIFE_PLAN_CCRC" in modalities or synthetic_archetype == "CONTINUING_CARE" or any(
                p.get("continuum_of_care_verified") is True for p in payloads
            ):
                nice_match.append(key)
                nice_fit_scores[key] = 100.0
            else:
                nice_mismatch.append(key)
                nice_fit_scores[key] = 0.0
        else:
            nice_unknown.append(key)

    reputation = get_public_reputation(row)
    web_rating = reputation.get("rating") if isinstance(reputation.get("rating"), (int, float)) else None
    web_review_count = reputation.get("review_count") if isinstance(reputation.get("review_count"), int) else None
    reputation_source = reputation.get("source") if reputation.get("identity_verified") is True else "UNKNOWN"
    reputation_observed_at = reputation.get("observed_at") if reputation.get("identity_verified") is True else "UNKNOWN"

    if web_rating is None or web_review_count is None:
        for payload in governed_evidence_runtime.agent_only_payloads(row):
            if web_rating is None and isinstance(payload.get("public_rating"), (int, float)):
                web_rating = float(payload.get("public_rating"))
                reputation_source = payload.get("public_reputation_source") or "AGENT_RESEARCH"
            if web_review_count is None and isinstance(payload.get("public_review_count"), int):
                web_review_count = int(payload.get("public_review_count"))
                reputation_source = payload.get("public_reputation_source") or reputation_source

    relevant_known = (
        len(must_pass)
        + len(nice_match)
        + len(nice_mismatch)
        + len(row.get("matched_needs") or [])
        + len(payloads)
        + (1 if reputation.get("identity_verified") is True else 0)
    )
    relevant_unknown = len(must_unknown) + len(nice_unknown) + len(row.get("unknown_critical_needs") or [])

    return {
        "hard_gate": "FAIL" if hard_fail else ("PENDING_VERIFICATION" if must_unknown else "PASS"),
        "must_pass": must_pass,
        "must_unknown": must_unknown,
        "must_pending_reasons": pending_reasons,
        "must_fail": hard_fail,
        "nice_match": nice_match,
        "nice_unknown": nice_unknown,
        "nice_mismatch": nice_mismatch,
        "nice_fit_scores": nice_fit_scores,
        "preference_consistency": "MISMATCH" if nice_mismatch else ("UNKNOWN" if nice_unknown else "MATCH"),
        "public_reputation": {
            "rating": web_rating if web_rating is not None else "UNKNOWN",
            "review_count": web_review_count if web_review_count is not None else "UNKNOWN",
            "source": reputation_source,
            "observed_at": reputation_observed_at,
            "identity_verified": reputation.get("identity_verified") is True,
            "role": "REPUTATION_ENRICHMENT_ONLY",
        },
        "relevant_evidence_known_count": relevant_known,
        "relevant_evidence_unknown_count": relevant_unknown,
    }


def intent_rank_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    hard_gate = str(fit.get("hard_gate") or "PENDING_VERIFICATION")
    gate_order = {"PASS": 0, "PENDING_VERIFICATION": 1, "FAIL": 2}.get(hard_gate, 1)
    nice_matches = len(fit.get("nice_match") or [])
    nice_mismatches = len(fit.get("nice_mismatch") or [])
    nice_scores = fit.get("nice_fit_scores") if isinstance(fit.get("nice_fit_scores"), dict) else {}
    community_fit = nice_scores.get("COMMUNITY_ENVIRONMENT_MATCH")
    community_fit_known = isinstance(community_fit, (int, float))

    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}

    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
    rating = reputation.get("rating")
    reviews = reputation.get("review_count")
    rating_known = isinstance(rating, (int, float))
    reviews_known = isinstance(reviews, int)

    care_setting = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
    care_status = _upper(care_setting.get("status"))
    modalities = {_upper(row.get("canonical_type"))}
    modalities.update(_upper(value) for value in row.get("housing_modalities") or [])
    if care_status == "POSSIBLE_FIT" and ("INDEPENDENT_LIVING" in modalities or "LIFE_PLAN_CCRC" in modalities):
        setting_order = 0
    else:
        setting_order = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}.get(care_status, 1)
    if "CONTINUUM_OF_CARE" in (fit.get("nice_match") or []) and care_status in {"PRIMARY_FIT", "POSSIBLE_FIT"}:
        setting_order = 0

    independent_capable = care_status in {"PRIMARY_FIT", "POSSIBLE_FIT"} and (
        "INDEPENDENT_LIVING" in modalities or "LIFE_PLAN_CCRC" in modalities
    )
    disciplinary = _upper(history.get("disciplinary_action"))
    latest_grade = _upper(history.get("latest_known_grade"))
    raw_counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}
    if independent_capable:
        disciplinary_order = 2 if disciplinary == "Y" else 0
        grade_order = {"C": 2, "D": 3}.get(latest_grade, 0)
        counts = {"C": int(raw_counts.get("C") or 0), "D": int(raw_counts.get("D") or 0)}
    else:
        disciplinary_order = 0 if disciplinary == "N" else (2 if disciplinary == "Y" else 1)
        counts = raw_counts
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}.get(latest_grade, 4)

    return (
        gate_order,
        setting_order,
        -nice_matches,
        nice_mismatches,
        0 if community_fit_known else 1,
        -float(community_fit) if community_fit_known else 0.0,
        disciplinary_order,
        grade_order,
        int(counts.get("D") or 0),
        int(counts.get("C") or 0),
        int(counts.get("B") or 0),
        -int(counts.get("A") or 0),
        0 if rating_known else 1,
        -float(rating) if rating_known else 0.0,
        0 if reviews_known else 1,
        -int(reviews) if reviews_known else 0,
        -int(fit.get("relevant_evidence_known_count") or 0),
        int(fit.get("relevant_evidence_unknown_count") or 0),
    )


def attach_client_intent_fit(rows: List[Dict[str, Any]], intent: Dict[str, Any]) -> None:
    for row in rows:
        row["client_intent_fit"] = evaluate_candidate_intent(row, intent)
        attach_explicit_intent_explanation(row, intent)


def attach_explicit_intent_explanation(row: Dict[str, Any], intent: Dict[str, Any]) -> None:
    """Surface specific requested properties only when their actual fit passed.

    Existing care explanations retain their evidence. Language support is not a
    selling point just because a provider has a language entry in its profile.
    """
    fit = row.get("client_intent_fit") or {}
    proofs = []
    for kind, passed, role in (
        ("must_haves", set(fit.get("must_pass") or []), "requirement"),
        ("nice_to_haves", set(fit.get("nice_match") or []), "preference"),
    ):
        for item in intent.get(kind) or []:
            key = item.get("key")
            if key not in passed:
                continue
            value = item.get("value")
            if key in {"REQUIRED_LANGUAGE_SUPPORT", "PREFERRED_LANGUAGE_SUPPORT"} and isinstance(value, str) and value.strip():
                text = f"Verified {value.strip()} language support matches your {role}."
            elif key == "REQUIRED_ACTIVITIES" and isinstance(value, list) and value:
                text = f"Verified activities match your requirement: {', '.join(str(activity) for activity in value)}."
            elif key == "KOSHER_MEALS":
                text = f"Verified kosher meals match your {role}."
            elif key in {"CONTINUUM_OF_CARE_REQUIRED", "CONTINUUM_OF_CARE"}:
                text = f"A verified care continuum matches your {role} to avoid another move as care needs change."
            else:
                continue
            proofs.append({"key": key, "role": role, "requested_value": value, "fit": "PASS" if role == "requirement" else "MATCH", "text": text})

    explanation = row.setdefault("explanation", {})
    # Retain a requested-language point only from the explicit proof above, so a
    # generic English capability cannot be advertised as a personalized match.
    existing = [str(text) for text in explanation.get("why_matches") or [] if not str(text).casefold().startswith("language support")]
    previous = {item.get("text") for item in explanation.get("explicit_intent_matches") or []}
    existing = [text for text in existing if text not in previous]
    explanation["explicit_intent_matches"] = proofs
    explanation["why_matches"] = list(dict.fromkeys([item["text"] for item in proofs] + existing))


__all__ = ["attach_client_intent_fit", "build_client_intent", "evaluate_candidate_intent", "intent_rank_key"]
