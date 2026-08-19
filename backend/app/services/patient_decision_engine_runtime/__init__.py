from __future__ import annotations

"""Integrated production decision runtime.

This layer composes governed care/regulatory matching, Human Intelligence, the
approved Resident–Senior Living Success Factors decision policy, market-scoped
agent evidence, and governed Knowledge Fabric / outcome-learning audit context.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.services.decision_agent_bridge import attach_agent_evidence_and_queue_gaps, social_evidence_sort_key
from app.services.decision_governance_runtime import attach_governed_knowledge_learning_and_audit
from app.services.human_intelligence_runtime_verified import (
    attach_human_person_fit,
    build_human_intelligence_context,
    has_explicit_person_fit_preference,
    person_fit_sort_key,
)
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


def build_patient_needs_profile(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    profile = _governed.build_patient_needs_profile(questionnaire_state, natural_language_query)
    human_context = build_human_intelligence_context(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    factor_policy = build_success_factor_trace(questionnaire_state, profile)
    profile["decision_intelligence"] = {
        "version": "decision-intelligence-runtime-v2",
        "human_intelligence": human_context,
        "success_factor_policy": factor_policy,
        "decision_readiness": human_context.get("decision_readiness"),
        "adaptive_questions": human_context.get("adaptive_questions") or [],
        "production_principle": "resident material unknown -> ask; facility material unknown -> market-scoped agent research; never infer a missing preference or convert unknown to mismatch",
    }
    return profile


_CARE_SETTING_ORDER = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}
_ELIGIBILITY_ORDER = {"ELIGIBLE": 0, "POTENTIALLY_ELIGIBLE": 1, "INSUFFICIENT_EVIDENCE": 2, "INELIGIBLE": 3}


def _stable_person_fit_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    setting = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
    setting_status = str(setting.get("status") or "POSSIBLE_FIT")
    eligibility = str(row.get("eligibility_status") or "INSUFFICIENT_EVIDENCE")
    patient_match = float(row.get("patient_match_score") or 0.0)
    return (_CARE_SETTING_ORDER.get(setting_status, 1), _ELIGIBILITY_ORDER.get(eligibility, 2), -patient_match, *person_fit_sort_key(row), *social_evidence_sort_key(row), original_index)


def _social_priority_is_explicit_high(human_context: Dict[str, Any]) -> bool:
    signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    return str(social.get("value") or "UNKNOWN").upper() == "HIGH"


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


def run_patient_decision_engine(questionnaire_state: Dict[str, Any], natural_language_query: str = "", limit: int = 50) -> Dict[str, Any]:
    core = _governed.run_patient_decision_engine(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query, limit=max(10000, int(limit or 50)))
    human_context = build_human_intelligence_context(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    rows = list(core.get("results") or [])
    attach_human_person_fit(rows, human_context)

    research_pool_size = min(len(rows), max(20, int(limit or 50)))
    agent_bridge = attach_agent_evidence_and_queue_gaps(rows[:research_pool_size], human_context)

    explicit_person_fit = has_explicit_person_fit_preference(human_context)
    explicit_social_fit = _social_priority_is_explicit_high(human_context)
    if explicit_person_fit or explicit_social_fit:
        indexed = list(enumerate(rows))
        indexed.sort(key=lambda pair: _stable_person_fit_key(pair[1], pair[0]))
        rows = [row for _, row in indexed]
        _reassign_rank_metadata(rows)

    selected = rows[: max(0, int(limit or 0))]
    core["results"] = selected
    core["result_count"] = len(selected)

    patient_profile = core.get("patient_needs_profile") if isinstance(core.get("patient_needs_profile"), dict) else {}
    presearch_policy = build_success_factor_trace(questionnaire_state, patient_profile)
    readiness = str(human_context.get("decision_readiness") or "UNKNOWN")
    finality = "PROVISIONAL_PENDING_RESIDENT_CLARIFICATION" if readiness != "READY" else str(agent_bridge.get("decision_finality") or "UNKNOWN")

    decision_intelligence = {
        "version": "decision-intelligence-runtime-v2",
        "human_intelligence": human_context,
        "success_factor_policy": presearch_policy,
        "person_fit_rank_effect": "ACTIVE_GOVERNED_PERSON_FIT" if (explicit_person_fit or explicit_social_fit) else "WAITING_FOR_EXPLICIT_PREFERENCE_OR_EVIDENCE",
        "agent_evidence_bridge": agent_bridge,
        "decision_finality": finality,
        "facility_person_fit_evidence": "Only market-scoped governed evidence may affect fit. Missing facility evidence becomes agent research; missing resident preference becomes a question.",
        "production_principle": "care/regulatory eligibility first; resident material unknown -> ask; facility material unknown -> market agent; verified fit evidence may order only when resident relevance is explicit",
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
        explanation["human_person_fit"] = row.get("human_person_fit")
        explanation["agent_person_fit_evidence"] = row.get("agent_person_fit_evidence") or []
        explanation["success_factor_summary"] = trace_summary
        audit_rows.append({"canonical_facility_id": row.get("canonical_facility_id"), "rank_position": row.get("rank_position"), "eligibility_status": row.get("eligibility_status"), "care_setting_fit": (row.get("care_setting_fit") or {}).get("status"), "matched_needs": [item.get("parameter_id") for item in row.get("matched_needs") or []], "unknown_critical_needs": [item.get("parameter_id") for item in row.get("unknown_critical_needs") or []], "success_factors_known_both_sides": trace_summary.get("known_on_both_sides") or [], "success_factors_facility_unknown": trace_summary.get("facility_evidence_unknown") or [], "agent_market_evidence_count": len(row.get("agent_person_fit_evidence") or [])})

    core["recommendation_audit_trace"] = {
        "model_version": "decision-intelligence-runtime-v2",
        "facts_used": {"patient_needs": [item.get("parameter_id") for item in patient_profile.get("needs") or []], "human_signals": human_context.get("signals") or {}},
        "decision_rules_applied": ["care_setting_fit_before_person_fit", "unknown_is_not_mismatch", "resident_material_unknown_triggers_next_best_question", "facility_material_unknown_triggers_market_agent_research", "agent_evidence_must_match_active_market", "explicit_preferences_before_inference", "success_factor_influence_classes_no_unvalidated_numeric_weights", "facility_size_not_independent_quality", "regulatory_evidence_governed_tie_break", "knowledge_fabric_requires_recommendation_eligibility_and_verification_gate", "outcomes_are_validation_only_without_governed_weight_change"],
        "evidence_references": ["Nevada HCQC / ALiS", "market-scoped official provider evidence", "CMS when applicable", "reports/RESIDENT_SENIOR_LIVING_SUCCESS_FACTORS_CANON_V1.md", "reports/RECOMMENDATION_INFLUENCE_MODEL_V1.md", "reports/RECOMMENDATION_REQUIRED_DATA_AND_NBQ_V1.md"],
        "agent_evidence_bridge": agent_bridge,
        "recommendations": audit_rows,
    }
    return attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state=questionnaire_state)


__all__ = ["_regulatory_index", "build_patient_needs_profile", "build_patient_comparison_context", "run_patient_decision_engine"]
