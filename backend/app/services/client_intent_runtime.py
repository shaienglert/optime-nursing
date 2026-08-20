from __future__ import annotations

"""Client-intent gate and governed post-gate ranking semantics."""

from typing import Any, Dict, List

from app.services.public_reputation_runtime import get_public_reputation


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _agent_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    return [item.get("payload") for item in evidence if isinstance(item.get("payload"), dict)]


def _governed_provider_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
    provider_evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else {}
    if provider_evidence:
        out.append(provider_evidence)
    life_plan = row.get("life_plan_primary_evidence") if isinstance(row.get("life_plan_primary_evidence"), dict) else {}
    if life_plan:
        direct: Dict[str, Any] = {}
        if str(life_plan.get("rehabilitation_source_url") or "").startswith("http"):
            direct["rehab_verified"] = True
            direct["pt_ot_verified"] = True
        modalities = {_upper(value) for value in row.get("housing_modalities") or []}
        if "LIFE_PLAN_CCRC" in modalities:
            direct["continuum_of_care_verified"] = True
        if direct:
            out.append(direct)
    return out


def build_client_intent(questionnaire_state: Dict[str, Any], natural_language_query: str, living_strategy: Dict[str, Any], human_context: Dict[str, Any]) -> Dict[str, Any]:
    query = str(natural_language_query or "").lower()
    signals = living_strategy.get("signals") if isinstance(living_strategy.get("signals"), dict) else {}
    household = living_strategy.get("household") if isinstance(living_strategy.get("household"), dict) else {}
    human_signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    must: List[Dict[str, Any]] = []
    nice: List[Dict[str, Any]] = []

    def add_must(key: str, reason: str, verification: str) -> None:
        must.append({"key": key, "reason": reason, "verification": verification})

    def add_nice(key: str, reason: str) -> None:
        nice.append({"key": key, "reason": reason})

    city = str(questionnaire_state.get("locationCity") or questionnaire_state.get("city") or "").strip().upper()
    if "las vegas" in query or city == "LAS VEGAS": add_must("LAS_VEGAS", "The requested market is Las Vegas.", "canonical city/state")
    if household.get("type") == "COUPLE": add_must("COUPLE_CORESIDENCE", "The couple wants to live together; a solution that cannot house both partners is not acceptable.", "unit/occupancy policy")
    if signals.get("adl_support_needed"): add_must("ADL_SUPPORT_AVAILABLE", "The recovering resident currently needs bathing/dressing assistance.", "service evidence or permitted outside-care model")
    if signals.get("rehabilitation_need_detected"): add_must("REHAB_PATH_AVAILABLE", "The recovery plan requires access to appropriate rehabilitation/PT/OT, either onsite or through a verified external pathway.", "rehab/PT/OT evidence")
    if signals.get("expected_recovery"): add_must("RECOVERY_TRANSITION_COMPATIBLE", "The solution must remain appropriate as temporary care needs decrease after recovery.", "care transition / outside-care / continuum policy")
    if signals.get("no_dementia"): add_must("NO_FORCED_MEMORY_PLACEMENT", "A cognitively intact resident should not be placed in a locked memory-care-only setting.", "care setting classification")

    compact = human_signals.get("compact_central_layout_preference") if isinstance(human_signals.get("compact_central_layout_preference"), dict) else {}
    if _upper(compact.get("value")) == "REQUIRED":
        add_must("COMPACT_CENTRAL_LAYOUT", "The resident's walking limit and refusal of wheelchair use make short internal distances essential.", "verified layout/internal walking-distance evidence")

    if signals.get("high_social_culture_priority"): add_nice("RICH_CULTURE_AND_ACTIVITIES", "The clients explicitly want substantial culture, classes, events and social opportunities.")
    community = human_signals.get("community_size_preference") if isinstance(human_signals.get("community_size_preference"), dict) else {}
    community_value = _upper(community.get("value"))
    if community_value not in {"UNKNOWN", "NO_PREFERENCE", "NONE"}: add_nice("COMMUNITY_ENVIRONMENT_MATCH", "The client expressed a community-size/environment preference.")
    if "transport" in query or "outings" in query or "trips" in query or "טיולים" in query: add_nice("TRANSPORTATION_AND_OUTINGS", "Transportation/outings are part of the desired lifestyle.")
    if any(token in query for token in ("dining", "restaurant", "food", "אוכל")): add_nice("DINING_EXPERIENCE", "Dining quality/experience is explicitly relevant.")
    if any(token in query for token in ("garden", "gardens", "gardening", "landscap", "grounds", "גינון", "גינות", "מטופח")):
        add_nice("GARDENS_AND_LANDSCAPING", "Landscaped grounds, gardens or a well-maintained outdoor environment are explicitly important.")

    return {"version": "client-intent-runtime-v1.3", "must_haves": must, "nice_to_haves": nice, "rule": "Client intent first -> verified MUST gate -> NICE-TO-HAVE ordering -> objective government/regulatory evidence -> public reputation -> relevant evidence completeness.", "unknown_policy": "A material MUST with UNKNOWN evidence is not a pass or a fail; it triggers clarification or research and prevents finality."}


def evaluate_candidate_intent(row: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    hard_fail: List[str] = []; must_unknown: List[str] = []; must_pass: List[str] = []; nice_match: List[str] = []; nice_unknown: List[str] = []; nice_fit_scores: Dict[str, float] = {}
    city = str(row.get("city") or "").strip().upper(); state = str(row.get("state") or "").strip().upper(); canonical_type = _upper(row.get("canonical_type"))
    person = row.get("human_person_fit") if isinstance(row.get("human_person_fit"), dict) else {}; size = person.get("community_size") if isinstance(person.get("community_size"), dict) else {}
    agent_payloads = _agent_payloads(row); provider_payloads = _governed_provider_payloads(row); payloads = [*agent_payloads, *provider_payloads]
    modalities = {_upper(value) for value in row.get("housing_modalities") or []}

    for must in intent.get("must_haves") or []:
        key = str(must.get("key") or "")
        if key == "LAS_VEGAS":
            (must_pass if state == "NV" and city == "LAS VEGAS" else hard_fail).append(key)
        elif key == "NO_FORCED_MEMORY_PLACEMENT":
            (hard_fail if canonical_type in {"MEMORY_CARE_ONLY", "LOCKED_MEMORY_CARE_ONLY"} else must_pass).append(key)
        elif key == "ADL_SUPPORT_AVAILABLE":
            if canonical_type == "ASSISTED_LIVING_RFG" or any(p.get("adl_support_verified") is True or p.get("outside_care_allowed_verified") is True for p in payloads): must_pass.append(key)
            elif any(p.get("adl_support_verified") is False and p.get("outside_care_allowed_verified") is False for p in payloads): hard_fail.append(key)
            else: must_unknown.append(key)
        elif key == "REHAB_PATH_AVAILABLE":
            if canonical_type == "SKILLED_NURSING" or any(p.get("rehab_verified") is True or p.get("pt_ot_verified") is True or p.get("pt_ot_external_path_verified") is True for p in payloads): must_pass.append(key)
            elif any(p.get("rehab_verified") is False and p.get("pt_ot_verified") is False and p.get("pt_ot_external_path_verified") is False for p in payloads): hard_fail.append(key)
            else: must_unknown.append(key)
        elif key == "COUPLE_CORESIDENCE":
            if any(p.get("couple_coresidence_verified") is True or p.get("same_apartment_transition_verified") is True for p in payloads): must_pass.append(key)
            elif any(p.get("couple_coresidence_verified") is False for p in payloads): hard_fail.append(key)
            else: must_unknown.append(key)
        elif key == "RECOVERY_TRANSITION_COMPATIBLE":
            if "LIFE_PLAN_CCRC" in modalities or any(p.get("outside_care_allowed_verified") is True or p.get("continuum_of_care_verified") is True or p.get("same_apartment_transition_verified") is True for p in payloads): must_pass.append(key)
            elif any(p.get("outside_care_allowed_verified") is False and p.get("continuum_of_care_verified") is False and p.get("same_apartment_transition_verified") is False for p in payloads): hard_fail.append(key)
            else: must_unknown.append(key)
        elif key == "COMPACT_CENTRAL_LAYOUT":
            if any(p.get("compact_layout_verified") is True or p.get("centralized_amenities_verified") is True or p.get("short_internal_distances_verified") is True for p in payloads): must_pass.append(key)
            elif any(p.get("compact_layout_verified") is False and p.get("centralized_amenities_verified") is False and p.get("short_internal_distances_verified") is False for p in payloads): hard_fail.append(key)
            else: must_unknown.append(key)
        else: must_unknown.append(key)

    for nice in intent.get("nice_to_haves") or []:
        key = str(nice.get("key") or "")
        if key == "RICH_CULTURE_AND_ACTIVITIES":
            if any(p.get("social_engagement_verified") is True for p in payloads): nice_match.append(key); nice_fit_scores[key] = 100.0
            else: nice_unknown.append(key)
        elif key == "COMMUNITY_ENVIRONMENT_MATCH":
            value = size.get("fit_score")
            if isinstance(value, (int, float)):
                score = float(value); nice_fit_scores[key] = score
                (nice_match if score > 0 else nice_unknown).append(key)
            else: nice_unknown.append(key)
        elif key == "TRANSPORTATION_AND_OUTINGS":
            if any(p.get("transportation_verified") is True for p in payloads): nice_match.append(key); nice_fit_scores[key] = 100.0
            else: nice_unknown.append(key)
        elif key == "DINING_EXPERIENCE":
            if any(p.get("dining_verified") is True for p in payloads): nice_match.append(key); nice_fit_scores[key] = 100.0
            else: nice_unknown.append(key)
        elif key == "GARDENS_AND_LANDSCAPING":
            if any(p.get("gardens_verified") is True or p.get("landscaping_verified") is True or p.get("landscaped_grounds_verified") is True for p in payloads): nice_match.append(key); nice_fit_scores[key] = 100.0
            else: nice_unknown.append(key)

    reputation = get_public_reputation(row)
    web_rating = reputation.get("rating") if isinstance(reputation.get("rating"), (int, float)) else None
    web_review_count = reputation.get("review_count") if isinstance(reputation.get("review_count"), int) else None
    reputation_source = reputation.get("source") if reputation.get("identity_verified") is True else "UNKNOWN"
    reputation_observed_at = reputation.get("observed_at") if reputation.get("identity_verified") is True else "UNKNOWN"
    if web_rating is None or web_review_count is None:
        for payload in agent_payloads:
            if web_rating is None and isinstance(payload.get("public_rating"), (int, float)): web_rating = float(payload.get("public_rating")); reputation_source = payload.get("public_reputation_source") or "AGENT_RESEARCH"
            if web_review_count is None and isinstance(payload.get("public_review_count"), int): web_review_count = int(payload.get("public_review_count")); reputation_source = payload.get("public_reputation_source") or reputation_source

    relevant_known = len(must_pass) + len(nice_match) + len(row.get("matched_needs") or []) + len(agent_payloads) + len(provider_payloads) + (1 if reputation.get("identity_verified") is True else 0)
    relevant_unknown = len(must_unknown) + len(nice_unknown) + len(row.get("unknown_critical_needs") or [])
    return {"hard_gate": "FAIL" if hard_fail else ("PENDING_VERIFICATION" if must_unknown else "PASS"), "must_pass": must_pass, "must_unknown": must_unknown, "must_fail": hard_fail, "nice_match": nice_match, "nice_unknown": nice_unknown, "nice_fit_scores": nice_fit_scores, "public_reputation": {"rating": web_rating if web_rating is not None else "UNKNOWN", "review_count": web_review_count if web_review_count is not None else "UNKNOWN", "source": reputation_source, "observed_at": reputation_observed_at, "identity_verified": reputation.get("identity_verified") is True, "role": "REPUTATION_ENRICHMENT_ONLY"}, "relevant_evidence_known_count": relevant_known, "relevant_evidence_unknown_count": relevant_unknown}


def intent_rank_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}; hard_gate = str(fit.get("hard_gate") or "PENDING_VERIFICATION")
    gate_order = {"PASS": 0, "PENDING_VERIFICATION": 1, "FAIL": 2}.get(hard_gate, 1); nice_matches = len(fit.get("nice_match") or []); nice_scores = fit.get("nice_fit_scores") if isinstance(fit.get("nice_fit_scores"), dict) else {}
    community_fit = nice_scores.get("COMMUNITY_ENVIRONMENT_MATCH"); community_fit_known = isinstance(community_fit, (int, float))
    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}; disciplinary = _upper(history.get("disciplinary_action")); disciplinary_order = 0 if disciplinary == "N" else (2 if disciplinary == "Y" else 1)
    counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}; latest_grade = _upper(history.get("latest_known_grade")); grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}.get(latest_grade, 4)
    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}; rating = reputation.get("rating"); reviews = reputation.get("review_count"); rating_known = isinstance(rating, (int, float)); reviews_known = isinstance(reviews, int)
    return (gate_order, -nice_matches, 0 if community_fit_known else 1, -float(community_fit) if community_fit_known else 0.0, disciplinary_order, grade_order, int(counts.get("D") or 0), int(counts.get("C") or 0), int(counts.get("B") or 0), -int(counts.get("A") or 0), 0 if rating_known else 1, -float(rating) if rating_known else 0.0, 0 if reviews_known else 1, -int(reviews) if reviews_known else 0, -int(fit.get("relevant_evidence_known_count") or 0), int(fit.get("relevant_evidence_unknown_count") or 0), str(row.get("facility_name") or ""))


def attach_client_intent_fit(rows: List[Dict[str, Any]], intent: Dict[str, Any]) -> None:
    for row in rows: row["client_intent_fit"] = evaluate_candidate_intent(row, intent)


__all__ = ["attach_client_intent_fit", "build_client_intent", "evaluate_candidate_intent", "intent_rank_key"]
