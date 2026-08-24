from __future__ import annotations

"""Service package import governance.

Production resolves the public patient-decision-engine name to the integrated runtime.
Semantic AI owns the process from interview sequencing through governed recommendation
synthesis and next action; Guardian/rules constrain and validate. Client-intent READY
permits facility matching/research to begin, while unresolved facility MUST evidence
keeps recommendation finality provisional and never becomes a silent PASS.
"""

import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional


_GOVERNED_FULLNAME = f"{__name__}.patient_decision_engine"
_RUNTIME_DIR = Path(__file__).resolve().parent / "patient_decision_engine_runtime"
_RUNTIME_INIT = _RUNTIME_DIR / "__init__.py"

# Install cross-cutting semantic household governance before any service imports the
# living-strategy builder. This prevents bereavement language from becoming a false
# current-couple requirement anywhere in the runtime.
from app.services.living_strategy_guard_patch import install_patch as _install_living_strategy_guard
_install_living_strategy_guard()


def _agency_matches_for_row(row: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    access = row.get("care_partner_access") if isinstance(row.get("care_partner_access"), dict) else {}
    if access.get("outside_care_allowed_verified") is not True:
        return []
    matches: list[dict[str, Any]] = []
    for option in result.get("care_partner_options") or []:
        if not isinstance(option, dict):
            continue
        fit = option.get("care_agency_fit") if isinstance(option.get("care_agency_fit"), dict) else {}
        hard_gate = str(fit.get("hard_gate") or "UNKNOWN").upper()
        matches.append({
            "canonical_agency_id": option.get("agency_id"),
            "agency_name": option.get("agency_name"),
            "verification_status": "VERIFIED" if hard_gate == "PASS" else "PARTIALLY_VERIFIED",
            "service_area_match": "LAS_VEGAS_VALLEY_SERVICE" in (fit.get("matched") or []),
            "can_cover_required_services": not any(str(reason).startswith("MISSING_") for reason in (fit.get("hard_fail_reasons") or [])),
            "services": [item for item in (fit.get("matched") or []) if item in {"BATHING_ASSISTANCE", "DRESSING_ASSISTANCE", "TRANSFER_ASSISTANCE"}],
            "minimum_hours": option.get("minimum_billable_hours", "UNKNOWN"),
            "estimated_hourly_rate": option.get("hourly_rate", "UNKNOWN"),
            "availability_status": option.get("availability_status", "UNKNOWN"),
            "material_unknowns": fit.get("material_unknowns") or [],
            "source": option.get("primary_source_url") or "Nevada PCA operational evidence",
        })
    return matches


def _reconcile_adl_must(row: dict[str, Any]) -> None:
    solution = row.get("combined_care_solution") if isinstance(row.get("combined_care_solution"), dict) else {}
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    if not fit or "ADL_SUPPORT_AVAILABLE" not in set((fit.get("must_pass") or []) + (fit.get("must_unknown") or []) + (fit.get("must_fail") or [])):
        return
    passed = list(fit.get("must_pass") or [])
    unknown = list(fit.get("must_unknown") or [])
    failed = list(fit.get("must_fail") or [])
    for bucket in (passed, unknown, failed):
        while "ADL_SUPPORT_AVAILABLE" in bucket:
            bucket.remove("ADL_SUPPORT_AVAILABLE")
    coverage = str(solution.get("combined_must_coverage") or "PENDING_VERIFICATION")
    if coverage == "PASS":
        passed.append("ADL_SUPPORT_AVAILABLE")
    elif coverage == "FAIL":
        failed.append("ADL_SUPPORT_AVAILABLE")
    else:
        unknown.append("ADL_SUPPORT_AVAILABLE")
    fit["must_pass"] = passed
    fit["must_unknown"] = unknown
    fit["must_fail"] = failed
    fit["hard_gate"] = "FAIL" if failed else ("PENDING_VERIFICATION" if unknown else "PASS")
    fit["care_delivery_gate"] = {
        "status": coverage,
        "delivery_model": solution.get("delivery_model"),
        "reason": solution.get("reason"),
        "rule": "outside-care permission alone is not a care PASS; verified agency coverage is required",
    }


def _apply_combined_care_layer(result: dict[str, Any], questionnaire_state: dict[str, Any], natural_language_query: str, limit: int) -> dict[str, Any]:
    from app.services.client_intent_runtime import intent_rank_key
    from app.services.combined_care_solution_runtime import attach_combined_care_solutions

    rows = list(result.get("results") or [])
    for row in rows:
        row["external_care_agency_matches"] = _agency_matches_for_row(row, result)
    summary = attach_combined_care_solutions(rows, questionnaire_state, natural_language_query)
    for row in rows:
        _reconcile_adl_must(row)
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (*intent_rank_key(pair[1]), pair[0]))
    rows = [row for _, row in indexed]
    for position, row in enumerate(rows, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        row["rank_tie_status"] = "UNIQUE_RANK"
        row["tied_with"] = []
        row.setdefault("explanation", {})["combined_care_solution"] = row.get("combined_care_solution") or {}
    selected = rows[: max(0, int(limit or 0))]
    result["results"] = selected
    result["result_count"] = len(selected)
    result["combined_care_solution_policy"] = summary
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    decision["combined_care_solution"] = summary
    must_gate = decision.get("must_gate") if isinstance(decision.get("must_gate"), dict) else {}
    must_gate["combined_care_delivery_enforced"] = True
    must_gate["combined_care_rule"] = "Outside-care permission alone does not satisfy ADL_SUPPORT_AVAILABLE; a verified agency match covering required services is required."
    decision["must_gate"] = must_gate
    decision["combined_solution_principle"] = "Rank the complete solution: housing environment and care delivery are separate. A preferred intimate/independent setting stays viable when outside care is permitted, but the care MUST closes only after a verified agency match covers the required services."
    result["decision_intelligence"] = decision
    return result


def _decision_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return profile.get("decision_intelligence") if isinstance(profile.get("decision_intelligence"), dict) else {}


def _readiness_from_decision(decision: dict[str, Any]) -> str:
    direct = str(decision.get("decision_readiness") or "").upper()
    if direct:
        return direct
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    return str(human.get("decision_readiness") or "UNKNOWN").upper()


def _client_interview_blocked(readiness: str) -> bool:
    """Only unresolved client intent blocks matching; facility research is downstream work."""
    return readiness not in {"READY", "NEEDS_RESEARCH"}


def _mark_client_ready_for_research(decision: dict[str, Any], readiness: str) -> None:
    if readiness != "NEEDS_RESEARCH":
        return
    decision["client_decision_readiness"] = "READY"
    decision["facility_research_state"] = "RESEARCH_REQUIRED"
    decision["decision_finality"] = "PROVISIONAL_PENDING_FACILITY_RESEARCH"
    decision["recommendation_execution_allowed"] = False
    decision["readiness_separation_rule"] = "Client readiness and facility evidence readiness are separate. Facility research never reopens a completed client interview."


def _blocked_interview_result(profile: dict[str, Any], readiness: str) -> dict[str, Any]:
    decision = _decision_from_profile(profile)
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    questions = human.get("adaptive_questions") or decision.get("adaptive_questions") or []
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    process_owner = {
        "owner": "SEMANTIC_AI_PROCESS_OWNER",
        "status": "ACTIVE" if semantic.get("status") == "CONSULTED_AND_VALIDATED" else semantic.get("status", "UNKNOWN"),
        "process_phase": "CLARIFICATION",
        "next_best_action": {
            "action": "ASK_CLIENT",
            "question": (questions[0].get("question") if questions and isinstance(questions[0], dict) else None),
        },
        "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
    }
    return {
        "patient_needs_profile": profile,
        "results": [],
        "result_count": 0,
        "total_candidates_scored": 0,
        "availability_policy": "Recommendations are blocked until the governed AI interview has enough client evidence to begin research.",
        "care_setting_policy": {"status": "BLOCKED_PENDING_AI_INTERVIEW", "decision_intelligence": decision},
        "decision_intelligence": {
            **decision,
            "decision_finality": "BLOCKED_PENDING_AI_INTERVIEW",
            "recommendation_execution_allowed": False,
            "interview_owner": "SEMANTIC_AI",
            "process_owner": process_owner,
            "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
        },
        "recommendation_audit_trace": {
            "recommendation_execution_allowed": False,
            "blocked_before_facility_ranking": True,
            "reason": readiness,
            "adaptive_questions": questions,
            "semantic_ai": semantic,
            "process_owner": process_owner,
            "rule": "Only unresolved client intent may block facility matching. Facility research is downstream of a completed client interview.",
        },
    }


def _suppress_unverified_recommendations(result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    if decision.get("recommendation_execution_allowed") is True:
        return result
    candidate_count = len(result.get("results") or [])
    decision["research_candidate_count"] = candidate_count
    decision["recommendation_visibility"] = "BLOCKED_UNTIL_MUST_GATE_PASS"
    decision["recommendation_visibility_rule"] = "Candidate identities and ranking are not exposed while any material MUST remains unresolved."
    result["decision_intelligence"] = decision
    result["results"] = []
    result["result_count"] = 0
    result["availability_policy"] = "Facility candidates are being researched; recommendations remain hidden until the governed MUST gate passes."
    audit = result.get("recommendation_audit_trace") if isinstance(result.get("recommendation_audit_trace"), dict) else {}
    audit["recommendation_execution_allowed"] = False
    audit["blocked_before_recommendation_visibility"] = True
    audit["recommendations"] = []
    result["recommendation_audit_trace"] = audit
    return result


class _IntegratedRuntimeLoader(importlib.machinery.SourceFileLoader):
    def exec_module(self, module: ModuleType) -> None:
        super().exec_module(module)
        from app.services.decision_agent_bridge_fast import attach_agent_evidence_and_queue_gaps_fast
        module.attach_agent_evidence_and_queue_gaps = attach_agent_evidence_and_queue_gaps_fast

        original = getattr(module, "run_patient_decision_engine", None)
        profile_builder = getattr(module, "build_patient_needs_profile", None)
        if not callable(original) or not callable(profile_builder) or getattr(original, "_combined_care_wrapped", False):
            return

        def wrapped(questionnaire_state: dict[str, Any], natural_language_query: str = "", limit: int = 50):
            profile = profile_builder(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
            profile_readiness = "UNKNOWN"
            if isinstance(profile, dict):
                profile_decision = _decision_from_profile(profile)
                profile_readiness = _readiness_from_decision(profile_decision)
                if _client_interview_blocked(profile_readiness):
                    return _blocked_interview_result(profile, profile_readiness)
                _mark_client_ready_for_research(profile_decision, profile_readiness)

            internal_limit = max(500, int(limit or 50))
            result = original(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query, limit=internal_limit)
            if not isinstance(result, dict):
                return result
            decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
            readiness = _readiness_from_decision(decision)
            if _client_interview_blocked(readiness):
                runtime_profile = result.get("patient_needs_profile") if isinstance(result.get("patient_needs_profile"), dict) else profile
                return _blocked_interview_result(runtime_profile or {}, readiness)
            _mark_client_ready_for_research(decision, readiness)

            from app.services.semantic_facility_requirements import apply_semantic_facility_requirements
            from app.services.ai_process_owner_guard_patch import attach_ai_process_owner_guarded
            from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline

            result = apply_semantic_facility_requirements(result, research_limit=max(60, internal_limit))
            decision = result.setdefault("decision_intelligence", {})
            decision["interview_owner"] = "SEMANTIC_AI"
            decision["guardian_role"] = "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT"
            decision.setdefault("recommendation_execution_allowed", True)
            result = _apply_combined_care_layer(result, questionnaire_state, natural_language_query, internal_limit)
            result = apply_must_ai_nice_pipeline(result, questionnaire_state, natural_language_query, limit)
            result = attach_ai_process_owner_guarded(result, questionnaire_state, natural_language_query)
            return _suppress_unverified_recommendations(result)

        setattr(wrapped, "_combined_care_wrapped", True)
        setattr(wrapped, "_ai_interview_gate_wrapped", True)
        setattr(wrapped, "_ai_process_owner_wrapped", True)
        setattr(wrapped, "_must_ai_nice_pipeline_wrapped", True)
        module.run_patient_decision_engine = wrapped


class _GovernedDecisionEngineFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Optional[list[str]] = None, target: Optional[ModuleType] = None):
        if fullname != _GOVERNED_FULLNAME:
            return None
        loader = _IntegratedRuntimeLoader(fullname, str(_RUNTIME_INIT))
        return importlib.util.spec_from_file_location(fullname, _RUNTIME_INIT, loader=loader, submodule_search_locations=[str(_RUNTIME_DIR)])


if not any(isinstance(finder, _GovernedDecisionEngineFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _GovernedDecisionEngineFinder())
