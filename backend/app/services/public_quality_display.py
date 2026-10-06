"""Display-only public quality record for a recommended community.

Owner decision 2026-10-06: show the public, regulator-issued quality record (Nevada DPBH
inspection grades for assisted living; CMS Five-Star for nursing homes) next to a
recommendation. This module only DESCRIBES existing governed evidence. It does not rank,
score or filter anything -- the Regulatory / Quality Evidence Layer remains the single
authority for how the same evidence breaks ties.

Rules (AGENTS.md): missing information is not negative evidence; a record that does not
exist is reported as "no record", never as a low grade or a low rating; the two rating
systems are never merged or converted into each other.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

_NONE_STATEMENT = "No public inspection or rating record was found for this community. This is not a negative finding."
_ALIS_CAVEAT = "An A grade means the state found the community in compliance at inspection; it is not a measure of resident satisfaction."
_CMS_CAVEAT = "Medicare’s Five-Star rating covers inspections, staffing and quality measures; it is not a measure of fit for your family."


def _rating(value: Any) -> Optional[int]:
    text = str(value if value is not None else "").strip()
    return int(text) if text.isdigit() and 1 <= int(text) <= 5 else None


def _alis(history: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "latest_known_grade" not in history and "grade_counts" not in history:
        return None
    grade = str(history.get("latest_known_grade") or "").upper()
    counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}
    known = int(history.get("known_grade_count") or 0)
    below_a = {g: int(counts.get(g) or 0) for g in ("B", "C", "D") if int(counts.get(g) or 0) > 0}
    return {
        "kind": "NV_STATE_INSPECTION",
        "source_label": "Nevada Department of Public and Behavioral Health inspection records",
        "latest_grade": grade if grade in {"A", "B", "C", "D"} else None,
        "latest_grade_date": None if str(history.get("latest_known_grade_date") or "UNKNOWN").upper() == "UNKNOWN" else str(history.get("latest_known_grade_date")).split(" ")[0],
        "graded_inspections": known,
        "inspections_on_record": int(history.get("inspection_count") or 0),
        "grades_below_a": below_a,
        "disciplinary_action_on_record": str(history.get("disciplinary_action") or "").upper() == "Y",
        "source_url": history.get("source_url"),
        "caveat": _ALIS_CAVEAT,
    }


def _cms(canonical: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ccn = str(canonical.get("cms_ccn") or "").strip()
    if not ccn or ccn.upper() == "UNKNOWN":
        return None
    overall = _rating(canonical.get("cms_overall_rating"))
    parts = {
        "health_inspection": _rating(canonical.get("cms_health_inspection_rating")),
        "staffing": _rating(canonical.get("cms_staffing_rating")),
        "quality_measures": _rating(canonical.get("cms_quality_measure_rating")),
    }
    if overall is None and all(v is None for v in parts.values()):
        return None
    return {
        "kind": "CMS_FIVE_STAR",
        "source_label": "Medicare Care Compare (CMS Five-Star)",
        "overall": overall,
        **parts,
        "as_of": canonical.get("cms_processing_date") if str(canonical.get("cms_processing_date") or "UNKNOWN").upper() != "UNKNOWN" else None,
        "source_url": f"https://www.medicare.gov/care-compare/details/nursing-home/{ccn}",
        "caveat": _CMS_CAVEAT,
    }


def build_public_quality(row: Dict[str, Any], canonical: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}
    record = _alis(history) if history else None
    if record is None and isinstance(canonical, dict):
        record = _cms(canonical)
    if record is None:
        return {"kind": "NONE", "statement": _NONE_STATEMENT}
    return record


def attach_public_quality(rows) -> None:
    try:
        from app.services.facility_parameter_service import get_canonical_facility_index
        index = get_canonical_facility_index()
    except Exception:  # display enrichment must never break a recommendation
        index = {}
    for row in rows:
        row["public_quality"] = build_public_quality(row, index.get(str(row.get("canonical_facility_id") or "")))
