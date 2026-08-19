from __future__ import annotations

"""Integrated production decision runtime.

This layer composes the existing governed care/regulatory engine with Human
Intelligence. It does not import the historical frontend ranking engine because
that engine contains heuristic/synthetic facility inference that is not allowed
in the canonical production path.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.services.human_intelligence_runtime import (
    attach_human_person_fit,
    build_human_intelligence_context,
    has_explicit_person_fit_preference,
    person_fit_sort_key,
)


_SERVICES_DIR = Path(__file__).resolve().parent.parent
_GOVERNED_DIR = _SERVICES_DIR / "patient_decision_engine"
_GOVERNED_INIT = _GOVERNED_DIR / "__init__.py"
_GOVERNED_PRIVATE_NAME = "app.services._patient_decision_engine_governed"

_spec = importlib.util.spec_from_file_location(
    _GOVERNED_PRIVATE_NAME,
    _GOVERNED_INIT,
    submodule_search_locations=[str(_GOVERNED_DIR)],
)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load governed patient decision engine: {_GOVERNED_INIT}")
_governed = importlib.util.module_from_spec(_spec)
sys.modules[_GOVERNED_PRIVATE_NAME] = _governed
_spec.loader.exec_module(_governed)

build_patient_needs_profile = _governed.build_patient_needs_profile
build_patient_comparison_context = _governed.build_patient_comparison_context


_CARE_SETTING_ORDER = {
    "PRIMARY_FIT": 0,
    "POSSIBLE_FIT": 1,
    "OVERLEVEL": 2,
    "INSUFFICIENT_SETTING": 3,
}
_ELIGIBILITY_ORDER = {
    "ELIGIBLE": 0,
    "POTENTIALLY_ELIGIBLE": 1,
    "INSUFFICIENT_EVIDENCE": 2,
    "INELIGIBLE": 3,
}


def _stable_person_fit_key(row: Dict[str, Any], original_index: int) -> tuple[Any, ...]:
    setting = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
    setting_status = str(setting.get("status") or "POSSIBLE_FIT")
    eligibility = str(row.get("eligibility_status") or "INSUFFICIENT_EVIDENCE")
    patient_match = float(row.get("patient_match_score") or 0.0)
    return (
        _CARE_SETTING_ORDER.get(setting_status, 1),
        _ELIGIBILITY_ORDER.get(eligibility, 2),
        -patient_match,
        *person_fit_sort_key(row),
        original_index,
    )


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
            row["tie_break_explanation_vs_next"] = {
                "why_ranked_above": "Explicit community-size preference changed the person-fit order using Nevada official bed-count evidence.",
                "deciding_dimension": "human_person_fit.community_size",
                "remained_equal": ["care_setting_fit", "eligibility", "patient_match"],
                "remaining_unknown": ["social_transition_fit", "independence_fit"],
            }


def run_patient_decision_engine(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    # Ask the governed engine for the whole canonical market so Human Intelligence
    # can affect selection before truncation. Care-setting and evidence governance
    # remain the primary gates.
    core = _governed.run_patient_decision_engine(
        questionnaire_state=questionnaire_state,
        natural_language_query=natural_language_query,
        limit=max(10000, int(limit or 50)),
    )

    human_context = build_human_intelligence_context(
        questionnaire_state=questionnaire_state,
        natural_language_query=natural_language_query,
    )
    rows = list(core.get("results") or [])
    attach_human_person_fit(rows, human_context)

    explicit_person_fit = has_explicit_person_fit_preference(human_context)
    if explicit_person_fit:
        indexed = list(enumerate(rows))
        indexed.sort(key=lambda pair: _stable_person_fit_key(pair[1], pair[0]))
        rows = [row for _, row in indexed]
        _reassign_rank_metadata(rows)

    selected = rows[: max(0, int(limit or 0))]
    core["results"] = selected
    core["result_count"] = len(selected)
    core["decision_intelligence"] = {
        "version": "decision-intelligence-runtime-v1",
        "human_intelligence": human_context,
        "person_fit_rank_effect": "ACTIVE" if explicit_person_fit else "WAITING_FOR_EXPLICIT_PREFERENCE",
        "facility_person_fit_evidence": "Nevada HCQC / ALiS official bed count; lifestyle/social evidence remains UNKNOWN unless separately verified",
        "production_principle": "care/regulatory eligibility first; evidence-backed person fit before regulatory tie-break when explicitly supplied",
    }

    # Put the new evidence inside the existing explanation object as well. This
    # keeps it visible even to older API contracts while dedicated response fields
    # are rolled forward.
    readiness = human_context.get("decision_readiness")
    questions = human_context.get("adaptive_questions") or []
    for row in selected:
        explanation = row.setdefault("explanation", {})
        explanation["decision_readiness"] = readiness
        explanation["adaptive_questions"] = questions
        explanation["human_person_fit"] = row.get("human_person_fit")

    return core


__all__ = [
    "build_patient_needs_profile",
    "build_patient_comparison_context",
    "run_patient_decision_engine",
]
