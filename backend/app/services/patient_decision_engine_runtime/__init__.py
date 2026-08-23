from __future__ import annotations

"""Integrated production decision runtime."""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.services.client_intent_runtime import attach_client_intent_fit, build_client_intent, intent_rank_key
from app.services.decision_agent_bridge import attach_agent_evidence_and_queue_gaps
from app.services.decision_governance_runtime import attach_governed_knowledge_learning_and_audit
from app.services.human_intelligence_runtime_verified import attach_human_person_fit, build_human_intelligence_context, has_explicit_person_fit_preference, person_fit_sort_key
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.personal_care_agency_runtime import build_care_agency_requirements, build_verified_care_partner_context
from app.services.provider_housing_runtime import attach_provider_housing_evidence
from app.services.success_factor_runtime import build_success_factor_trace, summarize_trace

_SERVICES_DIR = Path(__file__).resolve().parent.parent
_GOVERNED_DIR = _SERVICES_DIR / "patient_decision_engine"
_GOVERNED_INIT = _GOVERNED_DIR / "__init__.py"
_GOVERNED_PRIVATE_NAME = "app.services._patient_decision_engine_governed"
_spec = importlib.util.spec_from_file_location(_GOVERNED_PRIVATE_NAME, _GOVERNED_INIT, submodule_search_locations=[str(_GOVERNED_DIR)])
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load governed patient decision engine: {_GOVERNED_INIT}")
_governed = importlib.util.module_from_spec(_spec)
sys.modules[_GOVERNED_PRIVATE_NAME] = _governed
_spec.loader.exec_module(_governed)
_regulatory_index = _governed._regulatory_index
build_patient_comparison_context = _governed.build_patient_comparison_context


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


def _merge_strategy_questions(human_context: Dict[str, Any], strategy: Dict[str, Any]) -> None:
    questions = list(human_context.get("adaptive_questions") or [])
    existing = {str(item.get("question_key") or "") for item in questions}
    for item in strategy.get("material_questions") or []:
        key = str(item.get("question_key") or "")
        if not key or key in existing:
            continue
        questions.append(item)
        existing.add(key)
    human_context["adaptive_questions"] = questions
    human_context["living_strategy"] = strategy
    if questions:
        human_context["decision_readiness"] = "NEEDS_CLARIFICATION"


def build_patient_needs_profile(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    profile = _governed.build_patient_needs_profile(questionnaire_state, natural_language_query)
    strategy = build_living_strategy_context(questionnaire_state, natural_language_query)
    _apply_strategy_needs(profile, strategy)
    human_context = build_human_intelligence_context(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    _merge_strategy_questions(human_context, strategy)
    client_intent = build_client_intent(questionnaire_state, natural_language_query, strategy, human_context)
    factor_policy = build_success_factor_trace(questionnaire_state, profile)
    profile["living_strategy"] = strategy
    profile["client_intent"] = client_intent
    profile["decision_intelligence"] = {
        "version": "decision-intelligence-runtime-v3.1",
        "human_intelligence": human_context,
        "living_strategy": strategy,
        "client_intent": client_intent,
        "success_factor_policy": factor_policy,
        "decision_readiness": human_context.get("decision_readiness"),
        "adaptive_questions": human_context.get("adaptive_questions") or [],
        "production_principle": "client intent first; verified MUST gate; NICE-TO-HAVE ordering; then objective government/regulatory evidence, public reputation and relevant evidence completeness; UNKNOWN material facts trigger questions or research",
    }
    return profile


_CARE_SETTING_ORDER = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}
_ELIGIBILITY_ORDER = {"ELIGIBLE": 0, "POTENTIALLY_ELIGIBLE": 1, "INSUFFICIENT_EVIDENCE": 2, "INELIGIBLE": 3}


def _stable_pre_agent_fit_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    intent = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    gate = str(intent.get("hard_gate") or "PENDING_VERIFICATION")
    gate_order = {"PASS": 0, "PENDING_VERIFICATION": 1, "FAIL": 2}.get(gate, 1)
    setting = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
    return (
        gate_order,
        _CARE_SETTING_ORDER.get(str(setting.get("status") or "POSSIBLE_FIT"), 1),
        _ELIGIBILITY_ORDER.get(str(row.get("eligibility_status") or "INSUFFICIENT_EVIDENCE"), 2),
        *person_fit_sort_key(row),
        -float(row.get("patient_match_score") or 0.0),
        original_index,
    )


def _stable_final_intent_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    return (*intent_rank_key(row), original_index)


def _social_priority_is_explicit_high(human_context: Dict[str, Any]) -> bool:
    signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    value = str(social.get("value") or "UNKNOWN").upper()
    if value == "HIGH":
        return True
    strategy = human_context.get("living_strategy") if isinstance(human_context.get("living_strategy"), dict) else {}
    strategy_signals = strategy.get("signals") if isinstance(strategy.get("signals"), dict) else {}
    return bool(strategy_signals.get("high_social_culture_priority"))


def _rank_effect(explicit_person_fit: bool, explicit_social_fit: bool) -> str:
    if explicit_social_fit:
        return "ACTIVE_CLIENT_INTENT_NICE_TO_HAVE"
    if explicit_person_fit:
        return "ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE"
    return "ACTIVE_MUST_GATE_OBJECTIVE_EVIDENCE"


def _reassign_rank_metadata(rows: List[Dict[str, Any]]) -> None:
    for position, row in enumerate(rows, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        row["rank_tie_status"] = "UNIQUE_RANK"
        row["tied_with"] = []
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        row.setdefault("explanation", {})["ranking_sequence"] = {
            "must_gate": fit.get("hard_gate"),
            "must_pass": fit.get("must_pass") or [],
            "must_unknown": fit.get("must_unknown") or [],
            "nice_match": fit.get("nice_match") or [],
            "government_regulatory_then_public_reputation_then_evidence_completeness": True,
        }


def _row_modalities(row: Dict[str, Any]) -> set[str]:
    modalities = {str(row.get("canonical_type") or "UNKNOWN").upper()}
    modalities.update(str(value or "UNKNOWN").upper() for value in row.get("housing_modalities") or [])
    return modalities


def _strategy_universe_status(rows: List[Dict[str, Any]], strategy: Dict[str, Any]) -> Dict[str, Any]:
    leading = [
        item for item in (strategy.get("strategy_candidates") or [])
        if int(item.get("rank_hint") or 99) <= 2
    ]
    strategy_ids = {str(item.get("strategy_id") or "") for item in leading}
    rank_one_ids = {
        str(item.get("strategy_id") or "")
        for item in leading
        if int(item.get("rank_hint") or 99) == 1
    }
    types = {str(row.get("canonical_type") or "UNKNOWN").upper() for row in rows}
    modalities = set(types)
    for row in rows:
        modalities.update(_row_modalities(row))

    has_il = "INDEPENDENT_LIVING" in modalities
    has_ccrc = any("CCRC" in value or "LIFE_PLAN" in value for value in modalities)
    has_assisted = "ASSISTED_LIVING_RFG" in modalities or "ASSISTED_LIVING" in modalities
    has_skilled = "SKILLED_NURSING" in modalities
    has_primary_fit = any(
        str((row.get("care_setting_fit") or {}).get("status") or "").upper() == "PRIMARY_FIT"
        for row in rows
    )

    requirements = {
        "INDEPENDENT_LIVING": has_il,
        "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE": has_il,
        "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING": has_il and has_skilled,
        "ASSISTED_LIVING": has_assisted or has_primary_fit,
        "MEMORY_CARE": has_primary_fit,
        "SHORT_STAY_SKILLED_NURSING_REHAB": has_skilled,
        "LIFE_PLAN_CCRC": has_ccrc,
        "LIFE_PLAN_CCRC_WITH_MEMORY_CONTINUUM": has_ccrc and has_primary_fit,
    }
    evaluated_rank_one = {sid: requirements[sid] for sid in rank_one_ids if sid in requirements}
    complete = all(evaluated_rank_one.values()) if evaluated_rank_one else has_primary_fit
    missing_classes = sorted(sid for sid, present in evaluated_rank_one.items() if not present)

    return {
        "status": "SUFFICIENT_FOR_LEADING_STRATEGIES" if complete else "INCOMPLETE_FOR_LEADING_STRATEGIES",
        "leading_strategy_ids": sorted(strategy_ids),
        "rank_one_strategy_ids": sorted(rank_one_ids),
        "canonical_types_present": sorted(types),
        "housing_modalities_present": sorted(modalities),
        "missing_classes": missing_classes,
        "rule": "Do not present a facility ranking as final when the non-rejected canonical universe cannot represent every rank-1 living strategy.",
    }


def _strategy_research_pool(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    base_count = max(20, int(limit or 50))
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: Dict[str, Any]) -> None:
        canonical_id = str(row.get("canonical_facility_id") or row.get("canonical_id") or "")
        key = canonical_id or f"ROW-{id(row)}"
        if key in seen:
            return
        seen.add(key)
        selected.append(row)

    for row in rows[:base_count]:
        add(row)

    for row in rows:
        modalities = _row_modalities(row)
        if modalities & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}:
            add(row)

    return selected[: max(base_count, 60)]


def _care_partner_layer(strategy: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    strategy_ids = {str(item.get("strategy_id") or "") for item in strategy.get("strategy_candidates") or []}
    if "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE" not in strategy_ids:
        return {
            "status": "NOT_APPLICABLE",
            "licensed_valley_universe_count": 363,
            "operationally_verified_count": 3,
            "candidate_options": [],
            "rule": "The PCA layer activates only when Independent Living plus temporary personal care is a governed strategy candidate.",
        }

    query = str(natural_language_query or "").lower()
    assistance = str(questionnaire_state.get("assistanceLevel") or "").lower()
    combined = f"{query} {assistance}"
    bathing = any(token in combined for token in ("bath", "shower"))
    dressing = any(token in combined for token in ("dress", "socks", "shoes"))
    transfer = any(token in combined for token in ("transfer", "mobility", "walker", "wheelchair"))
    signals = strategy.get("signals") if isinstance(strategy.get("signals"), dict) else {}
    if signals.get("adl_support_needed") and not any((bathing, dressing, transfer)):
        bathing = True
        dressing = True

    preferred_languages: List[str] = []
    hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    language_profile = hi.get("languageProfile") if isinstance(hi.get("languageProfile"), dict) else {}
    preferred_language = str(language_profile.get("preferredSpokenLanguage") or "").strip()
    if preferred_language:
        preferred_languages.append(preferred_language)

    requirements = build_care_agency_requirements(
        temporary_adl_support=True,
        bathing=bathing,
        dressing=dressing,
        transfer=transfer,
        preferred_languages=preferred_languages,
    )
    return build_verified_care_partner_context(requirements, limit=10)


def _attach_facility_care_partner_access(rows: List[Dict[str, Any]], care_partner_layer: Dict[str, Any]) -> None:
    if care_partner_layer.get("status") == "NOT_APPLICABLE":
        return
    for row in rows:
        if "INDEPENDENT_LIVING" not in _row_modalities(row):
            continue
        evidence = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
        facts = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else {}
        outside = facts.get("outside_care_allowed_verified", "UNKNOWN")
        if outside is True:
            access = "OUTSIDE_AGENCY_PATH_VERIFIED"
        elif outside is False:
            access = "OUTSIDE_AGENCY_NOT_ALLOWED"
        else:
            access = "FACILITY_AGENCY_ACCESS_UNKNOWN"
        row["care_partner_access"] = {
            "status": access,
            "outside_care_allowed_verified": outside,
            "candidate_agency_count": len(care_partner_layer.get("candidate_options") or []) if outside is True else 0,
            "rule": "Agency candidates are not attached to a facility unless the facility/provider evidence permits an outside care path; preferred/on-site/required agency relationships require separate evidence.",
        }


def run_patient_decision_engine(questionnaire_state: Dict[str, Any], natural_language_query: str = "", limit: int = 50) -> Dict[str, Any]:
    strategy = build_living_strategy_context(questionnaire_state, natural_language_query)
    core = _governed.run_patient_decision_engine(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query, limit=max(10000, int(limit or 50)))
    patient_profile = core.get("patient_needs_profile") if isinstance(core.get("patient_needs_profile"), dict) else {}
    _apply_strategy_needs(patient_profile, strategy)
    patient_profile["living_strategy"] = strategy

    human_context = build_human_intelligence_context(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    _merge_strategy_questions(human_context, strategy)
    client_intent = build_client_intent(questionnaire_state, natural_language_query, strategy, human_context)
    patient_profile["client_intent"] = client_intent

    rows = list(core.get("results") or [])
    attach_provider_housing_evidence(rows)
    attach_human_person_fit(rows, human_context)
    attach_client_intent_fit(rows, client_intent)

    indexed_pre_agent = list(enumerate(rows))
    indexed_pre_agent.sort(key=lambda pair: _stable_pre_agent_fit_key(pair[1], pair[0]))
    rows = [row for _, row in indexed_pre_agent]

    non_failed = [row for row in rows if ((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL")]
    research_pool = _strategy_research_pool(non_failed, int(limit or 50))
    agent_bridge = attach_agent_evidence_and_queue_gaps(research_pool, human_context)

    attach_client_intent_fit(rows, client_intent)
    survivors = [row for row in rows if ((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL")]
    rejected = [row for row in rows if ((row.get("client_intent_fit") or {}).get("hard_gate") == "FAIL")]
    indexed_final = list(enumerate(survivors))
    indexed_final.sort(key=lambda pair: _stable_final_intent_key(pair[1], pair[0]))
    ranked_survivors = [row for _, row in indexed_final]
    _reassign_rank_metadata(ranked_survivors)

    universe_status = _strategy_universe_status(ranked_survivors, strategy)
    care_partner_layer = _care_partner_layer(strategy, questionnaire_state, natural_language_query)
    _attach_facility_care_partner_access(ranked_survivors, care_partner_layer)
    selected = ranked_survivors[: max(0, int(limit or 0))]
    core["results"] = selected
    core["result_count"] = len(selected)
    core["must_gate_rejected_count"] = len(rejected)
    core["must_gate_survivor_count"] = len(survivors)
    core["care_partner_options"] = care_partner_layer.get("candidate_options") or []
    presearch_policy = build_success_factor_trace(questionnaire_state, patient_profile)
    readiness = str(human_context.get("decision_readiness") or "UNKNOWN")
    selected_must_unknown = sum(len((row.get("client_intent_fit") or {}).get("must_unknown") or []) for row in selected)
    if readiness != "READY":
        finality = "PROVISIONAL_PENDING_RESIDENT_CLARIFICATION"
    elif universe_status.get("status") != "SUFFICIENT_FOR_LEADING_STRATEGIES":
        finality = "PROVISIONAL_STRATEGY_UNIVERSE_INCOMPLETE"
    elif selected_must_unknown:
        finality = "PROVISIONAL_PENDING_MUST_VERIFICATION"
    else:
        finality = str(agent_bridge.get("decision_finality") or "UNKNOWN")

    decision_intelligence = {
        "version": "decision-intelligence-runtime-v3.1",
        "human_intelligence": human_context,
        "living_strategy": strategy,
        "client_intent": client_intent,
        "strategy_universe": universe_status,
        "care_partner_layer": care_partner_layer,
        "success_factor_policy": presearch_policy,
        "person_fit_rank_effect": _rank_effect(has_explicit_person_fit_preference(human_context), _social_priority_is_explicit_high(human_context)),
        "agent_evidence_bridge": agent_bridge,
        "decision_finality": finality,
        "must_gate": {"survivors": len(survivors), "rejected": len(rejected), "selected_must_unknown_count": selected_must_unknown},
        "ranking_order": ["CLIENT_INTENT", "MUST_GATE", "NICE_TO_HAVE", "GOVERNMENT_REGULATORY_DATA", "PUBLIC_REPUTATION", "RELEVANT_EVIDENCE_COMPLETENESS"],
        "facility_person_fit_evidence": "Only market-scoped governed evidence may affect fit. Missing MUST facility evidence becomes agent research; missing resident intent becomes a question.",
        "production_principle": "understand the client first; reject verified MUST mismatches; rank only survivors by NICE-TO-HAVE fit; then use government/regulatory facts, public reputation and evidence completeness; UNKNOWN never becomes a silent pass or fail",
    }
    core["decision_intelligence"] = decision_intelligence
    if isinstance(patient_profile, dict):
        patient_profile["decision_intelligence"] = decision_intelligence
    care_policy = core.get("care_setting_policy")
    if isinstance(care_policy, dict):
        care_policy["decision_intelligence"] = decision_intelligence

    questions = human_context.get("adaptive_questions") or []
    audit_rows: List[Dict[str, Any]] = []
    for row in selected:
        factor_trace = build_success_factor_trace(questionnaire_state, patient_profile, row)
        trace_summary = summarize_trace(factor_trace)
        row["success_factor_trace"] = factor_trace
        explanation = row.setdefault("explanation", {})
        explanation["decision_readiness"] = readiness
        explanation["decision_finality"] = finality
        explanation["adaptive_questions"] = questions
        explanation["living_strategy"] = strategy
        explanation["client_intent"] = client_intent
        explanation["client_intent_fit"] = row.get("client_intent_fit")
        explanation["strategy_universe"] = universe_status
        explanation["care_partner_access"] = row.get("care_partner_access") or {"status": "NOT_APPLICABLE"}
        explanation["human_person_fit"] = row.get("human_person_fit")
        explanation["agent_person_fit_evidence"] = row.get("agent_person_fit_evidence") or []
        explanation["success_factor_summary"] = trace_summary
        audit_rows.append({"canonical_facility_id": row.get("canonical_facility_id"), "rank_position": row.get("rank_position"), "eligibility_status": row.get("eligibility_status"), "care_setting_fit": (row.get("care_setting_fit") or {}).get("status"), "client_intent_fit": row.get("client_intent_fit") or {}, "care_partner_access": row.get("care_partner_access") or {}, "matched_needs": [item.get("parameter_id") for item in row.get("matched_needs") or []], "unknown_critical_needs": [item.get("parameter_id") for item in row.get("unknown_critical_needs") or []], "success_factors_known_both_sides": trace_summary.get("known_on_both_sides") or [], "success_factors_facility_unknown": trace_summary.get("facility_evidence_unknown") or [], "agent_market_evidence_count": len(row.get("agent_person_fit_evidence") or [])})

    core["recommendation_audit_trace"] = {
        "model_version": "decision-intelligence-runtime-v3.1",
        "facts_used": {"patient_needs": [item.get("parameter_id") for item in patient_profile.get("needs") or []], "human_signals": human_context.get("signals") or {}, "living_strategy_signals": strategy.get("signals") or {}, "household": strategy.get("household") or {}, "client_intent": client_intent, "care_partner_layer": care_partner_layer},
        "decision_rules_applied": ["client_intent_first", "verified_must_mismatch_rejected", "material_must_unknown_requires_verification", "nice_to_have_orders_survivors", "government_regulatory_after_fit", "public_reputation_after_regulatory", "evidence_completeness_after_reputation", "living_strategy_before_facility_ranking", "least_restrictive_safe_strategy", "temporary_recovery_separate_from_long_term_residence", "independent_living_temporary_care_uses_separate_licensed_pca_layer", "facility_agency_access_requires_provider_evidence", "pca_operational_unknowns_keep_care_partner_provisional", "couple_members_keep_separate_care_profiles", "unknown_is_not_mismatch", "resident_material_unknown_triggers_next_best_question", "facility_material_unknown_triggers_market_agent_research", "agent_evidence_must_match_active_market", "success_factor_influence_classes_no_unvalidated_numeric_weights", "facility_size_not_independent_quality", "knowledge_fabric_requires_recommendation_eligibility_and_verification_gate", "outcomes_are_validation_only_without_governed_weight_change"],
        "evidence_references": ["Nevada HCQC / ALiS", "Nevada PCA operational primary-source evidence", "market-scoped official provider evidence", "CMS when applicable", "public reputation only when source/identity/review count are verifiable", "reports/RESIDENT_SENIOR_LIVING_SUCCESS_FACTORS_CANON_V1.md", "reports/RECOMMENDATION_INFLUENCE_MODEL_V1.md", "reports/RECOMMENDATION_REQUIRED_DATA_AND_NBQ_V1.md"],
        "living_strategy": strategy,
        "client_intent": client_intent,
        "strategy_universe": universe_status,
        "care_partner_layer": care_partner_layer,
        "agent_evidence_bridge": agent_bridge,
        "recommendations": audit_rows,
    }
    return attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state=questionnaire_state)


__all__ = ["_regulatory_index", "build_patient_needs_profile", "build_patient_comparison_context", "run_patient_decision_engine"]