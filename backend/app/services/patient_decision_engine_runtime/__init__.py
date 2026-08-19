from __future__ import annotations

"""Integrated production decision runtime."""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.services.decision_agent_bridge import attach_agent_evidence_and_queue_gaps, social_evidence_sort_key
from app.services.decision_governance_runtime import attach_governed_knowledge_learning_and_audit
from app.services.human_intelligence_runtime_verified import attach_human_person_fit, build_human_intelligence_context, has_explicit_person_fit_preference, person_fit_sort_key
from app.services.living_strategy_runtime import build_living_strategy_context
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
    factor_policy = build_success_factor_trace(questionnaire_state, profile)
    profile["living_strategy"] = strategy
    profile["decision_intelligence"] = {
        "version": "decision-intelligence-runtime-v3",
        "human_intelligence": human_context,
        "living_strategy": strategy,
        "success_factor_policy": factor_policy,
        "decision_readiness": human_context.get("decision_readiness"),
        "adaptive_questions": human_context.get("adaptive_questions") or [],
        "production_principle": "choose the least-restrictive safe living/care strategy first; resident material unknown -> ask; facility material unknown -> market-scoped agent research; never infer a missing preference or convert unknown to mismatch",
    }
    return profile


_CARE_SETTING_ORDER = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}
_ELIGIBILITY_ORDER = {"ELIGIBLE": 0, "POTENTIALLY_ELIGIBLE": 1, "INSUFFICIENT_EVIDENCE": 2, "INELIGIBLE": 3}


def _stable_pre_agent_fit_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    setting = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
    return (
        _CARE_SETTING_ORDER.get(str(setting.get("status") or "POSSIBLE_FIT"), 1),
        _ELIGIBILITY_ORDER.get(str(row.get("eligibility_status") or "INSUFFICIENT_EVIDENCE"), 2),
        -float(row.get("patient_match_score") or 0.0),
        *person_fit_sort_key(row),
        original_index,
    )


def _stable_person_fit_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    return (
        *_stable_pre_agent_fit_key(row, original_index)[:-1],
        *social_evidence_sort_key(row),
        original_index,
    )


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
        return "ACTIVE_GOVERNED_PERSON_FIT"
    if explicit_person_fit:
        return "ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE"
    return "WAITING_FOR_EXPLICIT_PREFERENCE_OR_EVIDENCE"


def _reassign_rank_metadata(rows: List[Dict[str, Any]]) -> None:
    for position, row in enumerate(rows, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        row["rank_tie_status"] = "UNIQUE_RANK"
        row["tied_with"] = []
        following = rows[position] if position < len(rows) else None
        if following is None:
            continue
        current_person = row.get("human_person_fit") if isinstance(row.get("human_person_fit"), dict) else {}
        next_person = following.get("human_person_fit") if isinstance(following.get("human_person_fit"), dict) else {}
        current_size = current_person.get("community_size") if isinstance(current_person.get("community_size"), dict) else {}
        next_size = next_person.get("community_size") if isinstance(next_person.get("community_size"), dict) else {}
        if current_size.get("fit_score") != next_size.get("fit_score"):
            row["tie_break_explanation_vs_next"] = {"why_ranked_above": "Explicit community-style preference matched against verified licensed capacity; facility size is not a quality factor.", "deciding_dimension": "preference_congruence.community_environment", "remained_equal": ["care_setting_fit", "eligibility", "patient_match"], "remaining_unknown": ["social_climate", "autonomy_choice_fit", "resident_staff_relationship"]}
        elif social_evidence_sort_key(row) != social_evidence_sort_key(following):
            row["tie_break_explanation_vs_next"] = {"why_ranked_above": "Explicit social-engagement priority plus market-scoped agent evidence verified relevant engagement signals. Missing evidence elsewhere remains UNKNOWN, not negative.", "deciding_dimension": "social_connection_engagement.verified_agent_evidence", "remained_equal": ["care_setting_fit", "eligibility", "patient_match", "community_environment"], "remaining_unknown": ["social_climate_outcomes", "resident_staff_relationship"]}


def _strategy_universe_status(rows: List[Dict[str, Any]], strategy: Dict[str, Any]) -> Dict[str, Any]:
    strategy_ids = {str(item.get("strategy_id") or "") for item in strategy.get("strategy_candidates") or [] if int(item.get("rank_hint") or 99) <= 2}
    types = {str(row.get("canonical_type") or "UNKNOWN").upper() for row in rows}
    needs_il = bool(strategy_ids & {"INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE", "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"})
    has_il = "INDEPENDENT_LIVING" in types
    has_ccrc = any("CCRC" in t or "LIFE_PLAN" in t for t in types)
    complete = not needs_il or has_il or has_ccrc
    return {
        "status": "SUFFICIENT_FOR_LEADING_STRATEGIES" if complete else "INCOMPLETE_FOR_LEADING_STRATEGIES",
        "leading_strategy_ids": sorted(strategy_ids),
        "canonical_types_present": sorted(types),
        "missing_classes": [item for item, missing in (("INDEPENDENT_LIVING", needs_il and not has_il), ("LIFE_PLAN_CCRC", "LIFE_PLAN_CCRC" in strategy_ids and not has_ccrc)) if missing],
        "rule": "Do not present a facility ranking as final when the canonical universe cannot represent a leading living strategy.",
    }


def run_patient_decision_engine(questionnaire_state: Dict[str, Any], natural_language_query: str = "", limit: int = 50) -> Dict[str, Any]:
    strategy = build_living_strategy_context(questionnaire_state, natural_language_query)
    core = _governed.run_patient_decision_engine(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query, limit=max(10000, int(limit or 50)))
    patient_profile = core.get("patient_needs_profile") if isinstance(core.get("patient_needs_profile"), dict) else {}
    _apply_strategy_needs(patient_profile, strategy)
    patient_profile["living_strategy"] = strategy

    human_context = build_human_intelligence_context(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    _merge_strategy_questions(human_context, strategy)
    rows = list(core.get("results") or [])
    attach_human_person_fit(rows, human_context)

    explicit_person_fit = has_explicit_person_fit_preference(human_context)
    explicit_social_fit = _social_priority_is_explicit_high(human_context)

    if explicit_person_fit or explicit_social_fit:
        indexed_pre_agent = list(enumerate(rows))
        indexed_pre_agent.sort(key=lambda pair: _stable_pre_agent_fit_key(pair[1], pair[0]))
        rows = [row for _, row in indexed_pre_agent]

    research_pool_size = min(len(rows), max(20, int(limit or 50)))
    agent_bridge = attach_agent_evidence_and_queue_gaps(rows[:research_pool_size], human_context)

    if explicit_person_fit or explicit_social_fit:
        indexed = list(enumerate(rows))
        indexed.sort(key=lambda pair: _stable_person_fit_key(pair[1], pair[0]))
        rows = [row for _, row in indexed]
        _reassign_rank_metadata(rows)

    universe_status = _strategy_universe_status(rows, strategy)
    selected = rows[: max(0, int(limit or 0))]
    core["results"] = selected
    core["result_count"] = len(selected)
    presearch_policy = build_success_factor_trace(questionnaire_state, patient_profile)
    readiness = str(human_context.get("decision_readiness") or "UNKNOWN")
    if readiness != "READY":
        finality = "PROVISIONAL_PENDING_RESIDENT_CLARIFICATION"
    elif universe_status.get("status") != "SUFFICIENT_FOR_LEADING_STRATEGIES":
        finality = "PROVISIONAL_STRATEGY_UNIVERSE_INCOMPLETE"
    else:
        finality = str(agent_bridge.get("decision_finality") or "UNKNOWN")

    decision_intelligence = {
        "version": "decision-intelligence-runtime-v3",
        "human_intelligence": human_context,
        "living_strategy": strategy,
        "strategy_universe": universe_status,
        "success_factor_policy": presearch_policy,
        "person_fit_rank_effect": _rank_effect(explicit_person_fit, explicit_social_fit),
        "agent_evidence_bridge": agent_bridge,
        "decision_finality": finality,
        "facility_person_fit_evidence": "Only market-scoped governed evidence may affect fit. Missing facility evidence becomes agent research; missing resident preference becomes a question.",
        "production_principle": "living/care strategy before facility ranking; least-restrictive safe setting; temporary recovery care separated from long-term residence; couple members retain separate needs; resident material unknown -> ask; facility material unknown -> market agent",
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
        explanation["strategy_universe"] = universe_status
        explanation["human_person_fit"] = row.get("human_person_fit")
        explanation["agent_person_fit_evidence"] = row.get("agent_person_fit_evidence") or []
        explanation["success_factor_summary"] = trace_summary
        audit_rows.append({"canonical_facility_id": row.get("canonical_facility_id"), "rank_position": row.get("rank_position"), "eligibility_status": row.get("eligibility_status"), "care_setting_fit": (row.get("care_setting_fit") or {}).get("status"), "matched_needs": [item.get("parameter_id") for item in row.get("matched_needs") or []], "unknown_critical_needs": [item.get("parameter_id") for item in row.get("unknown_critical_needs") or []], "success_factors_known_both_sides": trace_summary.get("known_on_both_sides") or [], "success_factors_facility_unknown": trace_summary.get("facility_evidence_unknown") or [], "agent_market_evidence_count": len(row.get("agent_person_fit_evidence") or [])})

    core["recommendation_audit_trace"] = {
        "model_version": "decision-intelligence-runtime-v3",
        "facts_used": {"patient_needs": [item.get("parameter_id") for item in patient_profile.get("needs") or []], "human_signals": human_context.get("signals") or {}, "living_strategy_signals": strategy.get("signals") or {}, "household": strategy.get("household") or {}},
        "decision_rules_applied": ["living_strategy_before_facility_ranking", "least_restrictive_safe_strategy", "temporary_recovery_separate_from_long_term_residence", "couple_members_keep_separate_care_profiles", "care_setting_fit_before_person_fit", "unknown_is_not_mismatch", "resident_material_unknown_triggers_next_best_question", "facility_material_unknown_triggers_market_agent_research", "agent_evidence_must_match_active_market", "research_pool_follows_resident_relevant_pre_agent_rank", "explicit_preferences_before_inference", "success_factor_influence_classes_no_unvalidated_numeric_weights", "facility_size_not_independent_quality", "regulatory_evidence_governed_tie_break", "knowledge_fabric_requires_recommendation_eligibility_and_verification_gate", "outcomes_are_validation_only_without_governed_weight_change"],
        "evidence_references": ["Nevada HCQC / ALiS", "market-scoped official provider evidence", "CMS when applicable", "reports/RESIDENT_SENIOR_LIVING_SUCCESS_FACTORS_CANON_V1.md", "reports/RECOMMENDATION_INFLUENCE_MODEL_V1.md", "reports/RECOMMENDATION_REQUIRED_DATA_AND_NBQ_V1.md"],
        "living_strategy": strategy,
        "strategy_universe": universe_status,
        "agent_evidence_bridge": agent_bridge,
        "recommendations": audit_rows,
    }
    return attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state=questionnaire_state)


__all__ = ["_regulatory_index", "build_patient_needs_profile", "build_patient_comparison_context", "run_patient_decision_engine"]
