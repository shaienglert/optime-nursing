from __future__ import annotations

"""Service package import governance.

There are historically multiple decision-engine implementations in the repo:
``patient_decision_engine.py`` (legacy core), ``patient_decision_engine/``
(governed care/regulatory facade), and the integrated production runtime that
adds evidence-governed Human Intelligence. Production must always resolve the
public ``app.services.patient_decision_engine`` name to the integrated runtime.

The loader also applies the governed Combined Care Solution layer after the
integrated runtime finishes. This keeps housing fit separate from care delivery.

The interview gate is authoritative: Semantic AI manages the interview under
OPTIME Guardian/Learning Center constraints. Facility recommendation execution is
not allowed until the governed interview returns READY.
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
        matches.append(
            {
                "canonical_agency_id": option.get("agency_id"),
                "agency_name": option.get("agency_name"),
                "verification_status": "VERIFIED" if hard_gate == "PASS" else "PARTIALLY_VERIFIED",
                "service_area_match": "LAS_VEGAS_VALLEY_SERVICE" in (fit.get("matched") or []),
                "can_cover_required_services": not any(
                    str(reason).startswith("MISSING_") for reason in (fit.get("hard_fail_reasons") or [])
                ),
                "services": [
                    item for item in (fit.get("matched") or [])
                    if item in {"BATHING_ASSISTANCE", "DRESSING_ASSISTANCE", "TRANSFER_ASSISTANCE"}
                ],
                "minimum_hours": option.get("minimum_billable_hours", "UNKNOWN"),
                "estimated_hourly_rate": option.get("hourly_rate", "UNKNOWN"),
                "availability_status": option.get("availability_status", "UNKNOWN"),
                "material_unknowns": fit.get("material_unknowns") or [],
                "source": option.get("primary_source_url") or "Nevada PCA operational evidence",
            }
        )
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
    decision["combined_solution_principle"] = (
        "Rank the complete solution: housing environment and care delivery are separate. "
        "A preferred intimate/independent setting stays viable when outside care is permitted, "
        "but the care MUST closes only after a verified agency match covers the required services."
    )
    result["decision_intelligence"] = decision
    return result


def _decision_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    decision = profile.get("decision_intelligence") if isinstance(profile.get("decision_intelligence"), dict) else {}
    return decision


def _readiness_from_decision(decision: dict[str, Any]) -> str:
    direct = str(decision.get("decision_readiness") or "").upper()
    if direct:
        return direct
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    return str(human.get("decision_readiness") or "UNKNOWN").upper()


def _blocked_interview_result(profile: dict[str, Any], readiness: str) -> dict[str, Any]:
    decision = _decision_from_profile(profile)
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    questions = human.get("adaptive_questions") or decision.get("adaptive_questions") or []
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    return {
        "patient_needs_profile": profile,
        "results": [],
        "result_count": 0,
        "total_candidates_scored": 0,
        "availability_policy": "Recommendations are blocked until the governed AI interview is READY.",
        "care_setting_policy": {
            "status": "BLOCKED_PENDING_AI_INTERVIEW",
            "decision_intelligence": decision,
        },
        "decision_intelligence": {
            **decision,
            "decision_finality": "BLOCKED_PENDING_AI_INTERVIEW" if readiness != "NEEDS_RESEARCH" else "BLOCKED_PENDING_AI_RESEARCH",
            "recommendation_execution_allowed": False,
            "interview_owner": "SEMANTIC_AI",
            "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
        },
        "recommendation_audit_trace": {
            "recommendation_execution_allowed": False,
            "blocked_before_facility_ranking": True,
            "reason": readiness,
            "adaptive_questions": questions,
            "semantic_ai": semantic,
            "rule": "No facility ranking or recommendation execution before governed Semantic AI + OPTIME Guardian return READY.",
        },
    }


class _IntegratedRuntimeLoader(importlib.machinery.SourceFileLoader):
    def exec_module(self, module: ModuleType) -> None:
        super().exec_module(module)
        original = getattr(module, "run_patient_decision_engine", None)
        profile_builder = getattr(module, "build_patient_needs_profile", None)
        if not callable(original) or not callable(profile_builder) or getattr(original, "_combined_care_wrapped", False):
            return

        def wrapped(questionnaire_state: dict[str, Any], natural_language_query: str = "", limit: int = 50):
            # AI/Guardian interview runs before the recommendation engine. If it is
            # not READY, do not rank, score, research, or expose facilities.
            profile = profile_builder(
                questionnaire_state=questionnaire_state,
                natural_language_query=natural_language_query,
            )
            if isinstance(profile, dict):
                readiness = _readiness_from_decision(_decision_from_profile(profile))
                if readiness != "READY":
                    return _blocked_interview_result(profile, readiness)

            result = original(
                questionnaire_state=questionnaire_state,
                natural_language_query=natural_language_query,
                limit=limit,
            )
            if not isinstance(result, dict):
                return result

            # Defense in depth: the full runtime consults AI again while assembling
            # decision intelligence. A changed/non-READY result cannot leak ranking.
            decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
            readiness = _readiness_from_decision(decision)
            if readiness != "READY":
                runtime_profile = result.get("patient_needs_profile") if isinstance(result.get("patient_needs_profile"), dict) else profile
                return _blocked_interview_result(runtime_profile or {}, readiness)

            result.setdefault("decision_intelligence", {})["recommendation_execution_allowed"] = True
            result["decision_intelligence"]["interview_owner"] = "SEMANTIC_AI"
            return _apply_combined_care_layer(result, questionnaire_state, natural_language_query, limit)

        setattr(wrapped, "_combined_care_wrapped", True)
        setattr(wrapped, "_ai_interview_gate_wrapped", True)
        module.run_patient_decision_engine = wrapped


class _GovernedDecisionEngineFinder(importlib.abc.MetaPathFinder):
    """Resolve the public production decision-engine name to the integrated runtime."""

    def find_spec(
        self,
        fullname: str,
        path: Optional[list[str]] = None,
        target: Optional[ModuleType] = None,
    ):
        if fullname != _GOVERNED_FULLNAME:
            return None
        loader = _IntegratedRuntimeLoader(fullname, str(_RUNTIME_INIT))
        return importlib.util.spec_from_file_location(
            fullname,
            _RUNTIME_INIT,
            loader=loader,
            submodule_search_locations=[str(_RUNTIME_DIR)],
        )


if not any(isinstance(finder, _GovernedDecisionEngineFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _GovernedDecisionEngineFinder())
