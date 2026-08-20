from __future__ import annotations

"""Service package import governance.

There are historically multiple decision-engine implementations in the repo:
``patient_decision_engine.py`` (legacy core), ``patient_decision_engine/``
(governed care/regulatory facade), and the integrated production runtime that
adds evidence-governed Human Intelligence. Production must always resolve the
public ``app.services.patient_decision_engine`` name to the integrated runtime.

The loader also applies the governed Combined Care Solution layer after the
integrated runtime finishes. This keeps housing fit separate from care delivery:
a facility that permits outside care is not treated as satisfying a care MUST
until a verified agency match covers the required services.
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
    ranking_order = list(decision.get("ranking_order") or [])
    if "COMBINED_CARE_MUST_COVERAGE" not in ranking_order:
        try:
            must_index = ranking_order.index("MUST_GATE") + 1
        except ValueError:
            must_index = 1
        ranking_order.insert(must_index, "COMBINED_CARE_MUST_COVERAGE")
    decision["ranking_order"] = ranking_order
    decision["combined_solution_principle"] = (
        "Rank the complete solution: housing environment and care delivery are separate. "
        "A preferred intimate/independent setting stays viable when outside care is permitted, "
        "but the care MUST closes only after a verified agency match covers the required services."
    )
    result["decision_intelligence"] = decision
    return result


class _IntegratedRuntimeLoader(importlib.machinery.SourceFileLoader):
    def exec_module(self, module: ModuleType) -> None:
        super().exec_module(module)
        original = getattr(module, "run_patient_decision_engine", None)
        if not callable(original) or getattr(original, "_combined_care_wrapped", False):
            return

        def wrapped(questionnaire_state: dict[str, Any], natural_language_query: str = "", limit: int = 50):
            result = original(
                questionnaire_state=questionnaire_state,
                natural_language_query=natural_language_query,
                limit=limit,
            )
            if not isinstance(result, dict):
                return result
            return _apply_combined_care_layer(result, questionnaire_state, natural_language_query, limit)

        setattr(wrapped, "_combined_care_wrapped", True)
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
