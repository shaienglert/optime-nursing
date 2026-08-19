from __future__ import annotations

"""Governed production facade for the patient decision engine.

The legacy scorer remains the capability/evidence scorer. This facade adds the
missing care-setting decision layer so a more intensive setting does not outrank
a suitable residential setting merely because it has more verified clinical
capabilities. Nevada ALiS inspection history is used only as a governed tie-breaker
within otherwise similarly matched residential candidates.
"""

import base64
import gzip
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from app.services.facility_parameter_service import get_canonical_facility_index


_REPO_ROOT = Path(__file__).resolve().parents[4]
_LEGACY_MODULE_NAME = "app.services._patient_decision_engine_legacy"
_LEGACY_PATH = Path(__file__).resolve().parent.parent / "patient_decision_engine.py"
_REGULATORY_PATH = _REPO_ROOT / "database" / "las_vegas_regulatory_summary.b64"
_REGULATORY_TEXT_SHA256 = "17a9a1a1c0dc4c1eb8fe42b7de1bdc24c014cd216dbe039d82c996b540146575"
_REGULATORY_PAYLOAD_SHA256 = "a2b2fd299366d06367ba162744fab0f1366c66810e0f13ff448fa51233068840"
_REGULATORY_RECORD_COUNT = 313

_spec = importlib.util.spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load patient decision engine core: {_LEGACY_PATH}")
_legacy = importlib.util.module_from_spec(_spec)
sys.modules[_LEGACY_MODULE_NAME] = _legacy
_spec.loader.exec_module(_legacy)


# A payer must come from the user/evidence. Medicare is not a universal preference
# for residential senior living and must not silently favor SNFs.
def _governed_map_financial(questionnaire: Dict[str, Any], needs_by_id: Dict[str, Any]) -> None:
    budget = questionnaire.get("budget")
    if budget not in (None, "", 0):
        _legacy._add_need(
            needs_by_id,
            "published_rates",
            "PREFERENCE",
            "KNOWN",
            ["KNOWN", "UNKNOWN"],
            "FACILITY",
            "questionnaire.budget",
            1.0,
            "Prefer transparent pricing",
        )


_legacy._map_financial = _governed_map_financial
_legacy_build_patient_needs_profile = _legacy.build_patient_needs_profile


# The legacy NLP location list was Florida-only. Nevada production must recognize
# explicit Las Vegas Valley city mentions without guessing a city from weak text.
_GOVERNED_CITY_TOKENS = (
    ("north las vegas", "NORTH LAS VEGAS"),
    ("henderson", "HENDERSON"),
    ("las vegas", "LAS VEGAS"),
)


def _explicit_location_city(questionnaire: Dict[str, Any], natural_language_query: str) -> str | None:
    for key in ("locationCity", "location_city", "city"):
        value = str(questionnaire.get(key) or "").strip()
        lowered = value.lower()
        for token, canonical in _GOVERNED_CITY_TOKENS:
            if token == lowered:
                return canonical

    normalized = str(natural_language_query or "").lower()
    for token, canonical in _GOVERNED_CITY_TOKENS:
        if token in normalized:
            return canonical
    return None


def build_patient_needs_profile(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
) -> Dict[str, Any]:
    profile = _legacy_build_patient_needs_profile(questionnaire_state, natural_language_query)
    if profile.get("location_city"):
        return profile

    location_city = _explicit_location_city(questionnaire_state, natural_language_query)
    if not location_city:
        return profile

    profile["location_city"] = location_city
    mapping = profile.setdefault("natural_language_mapping", {})
    mapping["location_city"] = location_city
    extraction = mapping.setdefault("extraction", {})
    recognized = extraction.setdefault("recognized_tokens", [])
    token = location_city.lower()
    if token not in recognized:
        recognized.append(token)
    return profile


# The legacy runner resolves this symbol from its module globals at execution time,
# so patch it to the governed wrapper as well as exporting the wrapper publicly.
_legacy.build_patient_needs_profile = build_patient_needs_profile
build_patient_comparison_context = _legacy.build_patient_comparison_context


CARE_SETTING_ORDER = {
    "PRIMARY_FIT": 0,
    "POSSIBLE_FIT": 1,
    "OVERLEVEL": 2,
    "INSUFFICIENT_SETTING": 3,
}
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}


@lru_cache(maxsize=1)
def _regulatory_index() -> Dict[str, Dict[str, Any]]:
    text = _REGULATORY_PATH.read_text(encoding="utf-8").strip()
    actual_text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if actual_text_sha != _REGULATORY_TEXT_SHA256:
        raise RuntimeError(
            f"Las Vegas regulatory summary checksum mismatch: {actual_text_sha}"
        )
    decoded = gzip.decompress(base64.b64decode(text, validate=True))
    actual_payload_sha = hashlib.sha256(decoded).hexdigest()
    if actual_payload_sha != _REGULATORY_PAYLOAD_SHA256:
        raise RuntimeError(
            f"Las Vegas regulatory payload checksum mismatch: {actual_payload_sha}"
        )
    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or {}
    if payload.get("record_count") != _REGULATORY_RECORD_COUNT or len(records) != _REGULATORY_RECORD_COUNT:
        raise RuntimeError("Las Vegas regulatory summary must contain exactly 313 RFG records")
    return records


def _need_is_high_yes(needs: List[Dict[str, Any]], parameter_ids: set[str]) -> bool:
    for need in needs:
        if str(need.get("parameter_id") or "") not in parameter_ids:
            continue
        if str(need.get("requirement_level") or "").upper() not in {"REQUIRED", "HIGH"}:
            continue
        if str(need.get("desired_value") or "").upper() == "YES":
            return True
    return False


def _care_setting_context(profile: Dict[str, Any]) -> Dict[str, bool]:
    needs = profile.get("needs") or []
    return {
        "requires_skilled": _need_is_high_yes(
            needs,
            {"skilled_nursing_capabilities", "nursing_24_7", "post_stroke_neuro_evidence"},
        ),
        "requires_memory": _need_is_high_yes(needs, {"memory_care", "dementia_alz_programs"}),
        "needs_residential_assistance": _need_is_high_yes(
            needs,
            {"adl_support", "medication_support", "transfer_assistance"},
        ),
    }


def _memory_confirmed(canonical_row: Dict[str, Any]) -> bool:
    return str(canonical_row.get("memory_care_classification") or "").upper() == "CONFIRMED"


def _care_setting_fit(
    context: Dict[str, bool],
    result: Dict[str, Any],
    canonical_row: Dict[str, Any],
) -> Dict[str, str]:
    canonical_type = str(result.get("canonical_type") or canonical_row.get("canonical_type") or "UNKNOWN").upper()

    if context["requires_skilled"]:
        if canonical_type == "SKILLED_NURSING":
            return {"status": "PRIMARY_FIT", "reason": "Skilled/24-7 clinical care is a stated high-priority need."}
        return {"status": "INSUFFICIENT_SETTING", "reason": "The stated needs require a skilled clinical setting."}

    if context["requires_memory"]:
        if canonical_type == "ASSISTED_LIVING_RFG" and _memory_confirmed(canonical_row):
            return {"status": "PRIMARY_FIT", "reason": "Memory care is required and officially confirmed for this residential setting."}
        if canonical_type == "SKILLED_NURSING":
            return {"status": "POSSIBLE_FIT", "reason": "A skilled setting may be appropriate only if clinical needs also justify that intensity."}
        return {"status": "INSUFFICIENT_SETTING", "reason": "Required memory-care capability is not confirmed for this setting."}

    if context["needs_residential_assistance"]:
        if canonical_type == "ASSISTED_LIVING_RFG":
            return {"status": "PRIMARY_FIT", "reason": "Daily living assistance is needed without a stated skilled-nursing requirement."}
        if canonical_type == "SKILLED_NURSING":
            return {"status": "OVERLEVEL", "reason": "Skilled nursing is more intensive than the stated care needs; consider only if clinical assessment indicates it."}
        if canonical_type == "INDEPENDENT_LIVING":
            return {"status": "INSUFFICIENT_SETTING", "reason": "Independent living alone does not establish the daily assistance required by this profile."}
        return {"status": "POSSIBLE_FIT", "reason": "Care-setting fit requires direct verification."}

    if canonical_type == "INDEPENDENT_LIVING":
        return {"status": "PRIMARY_FIT", "reason": "No high-priority daily-care or skilled-care need is stated."}
    if canonical_type == "ASSISTED_LIVING_RFG":
        return {"status": "POSSIBLE_FIT", "reason": "Residential care may fit, but the stated profile does not require that level of assistance."}
    if canonical_type == "SKILLED_NURSING":
        return {"status": "OVERLEVEL", "reason": "No skilled-nursing need is stated."}
    return {"status": "POSSIBLE_FIT", "reason": "Care-setting fit requires direct verification."}


def _date_sort_value(value: Any) -> float:
    text = str(value or "").strip()
    if not text or text.upper() == "UNKNOWN":
        return 0.0
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M %p", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _regulatory_sort_tuple(row: Dict[str, Any]) -> tuple[Any, ...]:
    history = row.get("regulatory_history") or {}
    if not history:
        # UNKNOWN stays UNKNOWN. It sorts after known inspection evidence, not as a failure.
        return (1, GRADE_ORDER["UNKNOWN"], 0, 0, 0, 0, 0, 0.0)
    counts = history.get("grade_counts") or {}
    disciplinary = str(history.get("disciplinary_action") or "UNKNOWN").upper()
    disciplinary_order = 0 if disciplinary == "N" else (2 if disciplinary == "Y" else 1)
    latest_grade = str(history.get("latest_known_grade") or "UNKNOWN").upper()
    return (
        disciplinary_order,
        GRADE_ORDER.get(latest_grade, GRADE_ORDER["UNKNOWN"]),
        int(counts.get("D") or 0),
        int(counts.get("C") or 0),
        int(counts.get("B") or 0),
        -int(counts.get("A") or 0),
        -int(history.get("known_grade_count") or 0),
        -_date_sort_value(history.get("latest_known_grade_date")),
    )


def _result_sort_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    setting = row.get("care_setting_fit") or {}
    setting_order = CARE_SETTING_ORDER.get(str(setting.get("status") or "POSSIBLE_FIT"), 1)
    eligibility_order = _legacy.ELIGIBILITY_ORDER.get(str(row.get("eligibility_status") or "INSUFFICIENT_EVIDENCE"), 2)
    return (
        1 if str(row.get("eligibility_status") or "") == "INELIGIBLE" else 0,
        setting_order,
        eligibility_order,
        -(float(row.get("patient_match_score") or 0.0)),
        *_regulatory_sort_tuple(row),
        -(float(row.get("quality_safety_score") or 0.0)),
        -(float(row.get("staffing_score") or 0.0)),
        -(float(row.get("capability_depth_score") or 0.0)),
        -(float(row.get("patient_relevant_outcomes_score") or 0.0)),
        -(float(row.get("practical_fit_score") or 0.0)),
        str(row.get("facility_name") or ""),
        str(row.get("canonical_facility_id") or ""),
    )


def _governed_rank_signature(row: Dict[str, Any]) -> tuple[Any, ...]:
    setting = row.get("care_setting_fit") or {}
    return (
        setting.get("status"),
        row.get("eligibility_status"),
        row.get("patient_match_score"),
        _regulatory_sort_tuple(row),
        row.get("quality_safety_score"),
        row.get("staffing_score"),
        row.get("capability_depth_score"),
        row.get("patient_relevant_outcomes_score"),
        row.get("practical_fit_score"),
    )


def _deciding_dimension(current: Dict[str, Any], following: Dict[str, Any]) -> str:
    current_setting = (current.get("care_setting_fit") or {}).get("status")
    following_setting = (following.get("care_setting_fit") or {}).get("status")
    if current_setting != following_setting:
        return "care_setting_fit"
    if current.get("eligibility_status") != following.get("eligibility_status"):
        return "eligibility"
    if current.get("patient_match_score") != following.get("patient_match_score"):
        return "patient_match"
    if _regulatory_sort_tuple(current) != _regulatory_sort_tuple(following):
        return "regulatory_history"
    for field, dimension in (
        ("quality_safety_score", "quality_safety"),
        ("staffing_score", "staffing"),
        ("capability_depth_score", "capability_depth"),
        ("patient_relevant_outcomes_score", "patient_relevant_outcomes"),
        ("practical_fit_score", "practical_fit"),
    ):
        if current.get(field) != following.get(field):
            return dimension
    return "true_tie"


def _assign_governed_ranks(rows: List[Dict[str, Any]]) -> None:
    groups: Dict[tuple[Any, ...], List[str]] = {}
    for row in rows:
        signature = _governed_rank_signature(row)
        groups.setdefault(signature, []).append(str(row.get("canonical_facility_id") or ""))

    first_position: Dict[tuple[Any, ...], int] = {}
    for position, row in enumerate(rows, start=1):
        signature = _governed_rank_signature(row)
        first_position.setdefault(signature, position)
        rank = first_position[signature]
        group_ids = [item for item in groups[signature] if item]
        canonical_id = str(row.get("canonical_facility_id") or "")
        tied_with = [item for item in group_ids if item != canonical_id]

        row["rank_position"] = rank
        row["rank_tie_status"] = "JOINT_RANK" if tied_with else "UNIQUE_RANK"
        row["rank_display"] = f"Joint #{rank}" if tied_with else f"#{rank}"
        row["tied_with"] = tied_with

        following = rows[position] if position < len(rows) else None
        if following is None:
            row["tie_break_explanation_vs_next"] = {
                "why_ranked_above": "No lower-ranked candidate follows this result.",
                "deciding_dimension": "end_of_ranking",
                "remained_equal": [],
                "remaining_unknown": [],
            }
            continue

        deciding = _deciding_dimension(row, following)
        if deciding == "true_tie":
            why = "Materially equal across all governed ranking dimensions with available evidence."
        elif deciding == "regulatory_history":
            why = "Nevada HCQC / ALiS official regulatory history breaks an otherwise material tie."
        else:
            why = f"Ranked above the next candidate on governed {deciding.replace('_', ' ')} evidence."
        row["tie_break_explanation_vs_next"] = {
            "why_ranked_above": why,
            "deciding_dimension": deciding,
            "remained_equal": [],
            "remaining_unknown": [],
        }


def run_patient_decision_engine(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    # Score the complete canonical market first. Care-setting routing must happen
    # before truncation; otherwise an over-level SNF-only top-N cannot be corrected.
    core = _legacy.run_patient_decision_engine(
        questionnaire_state=questionnaire_state,
        natural_language_query=natural_language_query,
        limit=max(10000, int(limit or 50)),
    )

    profile = core.get("patient_needs_profile") or {}
    context = _care_setting_context(profile)
    canonical_index = get_canonical_facility_index()
    regulatory = _regulatory_index()
    results = list(core.get("results") or [])

    for row in results:
        canonical_id = str(row.get("canonical_facility_id") or "")
        canonical_row = canonical_index.get(canonical_id) or {}
        row["care_setting_fit"] = _care_setting_fit(context, row, canonical_row)
        if canonical_id in regulatory:
            row["regulatory_history"] = regulatory[canonical_id]

    results.sort(key=_result_sort_key)
    _assign_governed_ranks(results)
    selected = results[: max(0, int(limit or 0))]

    core["results"] = selected
    core["result_count"] = len(selected)
    core["care_setting_policy"] = {
        "version": "v1.1",
        "context": context,
        "principle": "least-intensive appropriate setting before excess capability",
        "regulatory_tie_break": "Nevada HCQC / ALiS official grade history; UNKNOWN remains UNKNOWN",
        "rank_metadata": "recomputed after governed Nevada sorting",
    }
    return core


__all__ = [
    "build_patient_needs_profile",
    "build_patient_comparison_context",
    "run_patient_decision_engine",
]
