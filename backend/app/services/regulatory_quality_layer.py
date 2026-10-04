"""Regulatory / Quality Evidence Layer -- one place for government and verified quality
evidence in ranking (owner, 2026-10-01, Finding 2).

Rules:
* Every governed source available for a facility is gathered here (Nevada ALiS history,
  inspection ratings, deficiencies, staffing). Nothing is converted into an artificial
  composite score: each measure stays in its own domain and units.
* Measures are used only to separate candidates that are otherwise equal on everything
  the family asked for (MUST, care fit, NICE).
* A measure separates a group only when EVERY member has it, from the same source family.
  A facility without the measure is never ranked below one with it (UNKNOWN is not
  negative evidence); the measure is simply not a valid basis for that group.
* Two different measures are never compared with each other. If no measure is shared,
  the group is a true tie.
* Name, load order, index or check time never decide rank. Members of a true tie share
  one rank position; the order they are listed in is stated to carry no meaning.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# (measure_id, layer, better) -- the declared priority. "better" is "lower" or "higher".
MEASURES: Tuple[Tuple[str, str, str], ...] = (
    ("alis_disciplinary_action", "GOVERNMENT_REGULATORY", "lower"),
    ("alis_latest_grade", "GOVERNMENT_REGULATORY", "lower"),
    ("alis_grade_counts", "GOVERNMENT_REGULATORY", "lower"),
    ("inspection_rating", "GOVERNMENT_REGULATORY", "higher"),
    ("deficiency_count", "GOVERNMENT_REGULATORY", "lower"),
    ("total_nurse_hours_per_resident_day", "GOVERNMENT_REGULATORY", "higher"),
    ("rn_hours_per_resident_day", "GOVERNMENT_REGULATORY", "higher"),
    ("staffing_turnover", "GOVERNMENT_REGULATORY", "lower"),
    ("public_rating", "PUBLIC_REPUTATION", "higher"),
    ("public_review_count", "PUBLIC_REPUTATION", "higher"),
    ("relevant_evidence_known_count", "RELEVANT_EVIDENCE", "higher"),
)
# Parameters whose verified value (and source) the core attaches for this layer.
# quality_measures is deliberately absent: its scale and direction are not established.
QUALITY_PARAMETERS = (
    "inspection_rating",
    "deficiency_count",
    "total_nurse_hours_per_resident_day",
    "rn_hours_per_resident_day",
    "staffing_turnover",
)
_GRADE = {"A": 0, "B": 1, "C": 2, "D": 3}


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def measure_values(row: Dict[str, Any]) -> Dict[str, Tuple[str, Any]]:
    """{measure_id: (source_family, comparable value)} for the measures this row has."""
    out: Dict[str, Tuple[str, Any]] = {}
    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}
    disciplinary = str(history.get("disciplinary_action") or "").upper()
    if disciplinary in {"Y", "N"}:
        out["alis_disciplinary_action"] = ("NV_ALIS", 1 if disciplinary == "Y" else 0)
    grade = str(history.get("latest_known_grade") or "").upper()
    if grade in _GRADE:
        out["alis_latest_grade"] = ("NV_ALIS", _GRADE[grade])
    counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}
    if int(history.get("known_grade_count") or 0) > 0:
        out["alis_grade_counts"] = ("NV_ALIS", (int(counts.get("D") or 0), int(counts.get("C") or 0), int(counts.get("B") or 0), -int(counts.get("A") or 0)))
    quality = row.get("regulatory_quality_evidence") if isinstance(row.get("regulatory_quality_evidence"), dict) else {}
    for parameter in QUALITY_PARAMETERS:
        item = quality.get(parameter)
        if isinstance(item, dict):
            value = _number(item.get("value"))
            if value is not None:
                out[parameter] = (str(item.get("source_family") or "UNKNOWN_SOURCE"), value)
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
    if _number(reputation.get("rating")) is not None:
        out["public_rating"] = (str(reputation.get("source") or "PUBLIC_REVIEWS"), _number(reputation.get("rating")))
    if isinstance(reputation.get("review_count"), int) and not isinstance(reputation.get("review_count"), bool):
        out["public_review_count"] = (str(reputation.get("source") or "PUBLIC_REVIEWS"), reputation["review_count"])
    known = fit.get("relevant_evidence_known_count")
    if isinstance(known, int) and not isinstance(known, bool):
        out["relevant_evidence_known_count"] = ("CASE_RELEVANT_EVIDENCE", known)
    return out


def _split(group: List[Dict[str, Any]], start: int, path: Tuple[Any, ...], out: List[Tuple[Tuple[Any, ...], Dict[str, Any], List[str]]], used: List[str]) -> None:
    if len(group) == 1:
        out.append((path, group[0], list(used)))
        return
    values = [measure_values(row) for row in group]
    for position in range(start, len(MEASURES)):
        measure, _layer, better = MEASURES[position]
        if not all(measure in v for v in values):
            continue
        families = {v[measure][0] for v in values}
        if len(families) != 1:
            continue  # different sources of "the same" measure are not comparable
        distinct = sorted({v[measure][1] for v in values}, reverse=(better == "higher"))
        if len(distinct) < 2:
            continue
        for rank, value in enumerate(distinct):
            subgroup = [row for row, v in zip(group, values) if v[measure][1] == value]
            _split(subgroup, position + 1, path + (rank,), out, used + [measure])
        return
    # No shared, comparable, differing measure: a true tie. Listing order carries no rank.
    for row in sorted(group, key=lambda r: str(r.get("canonical_facility_id") or "")):
        out.append((path, row, list(used)))


def rank_with_evidence_layer(rows: Sequence[Dict[str, Any]], base_key: Callable[[Dict[str, Any]], Tuple[Any, ...]], *, base_dimensions=None) -> List[Dict[str, Any]]:
    """Order rows by base_key (the family's own criteria), then separate base-equal groups
    with the layer. Sets row["rank_group_signature"]: rows sharing it are a true tie."""
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(base_key(row)), []).append(row)
    ranked: List[Dict[str, Any]] = []
    for base in sorted(groups):
        out: List[Tuple[Tuple[Any, ...], Dict[str, Any], List[str]]] = []
        _split(groups[base], 0, (), out, [])
        for path, row, used in out:
            row["rank_group_signature"] = (base, path)
            # Snapshot the comparator at the stage that actually orders this
            # universe. Later evidence refreshes must not rewrite its rationale.
            row["__rank_comparison_trace"] = {
                "base_values": base,
                "base_dimensions": tuple(base_dimensions) if base_dimensions is not None else None,
                "evidence_path": path,
                "evidence_measures": list(used),
                "measure_values": measure_values(row),
            }
            row["regulatory_quality_layer"] = {
                "measures_used_to_separate": used,
                "measures_available": sorted(measure_values(row)),
                "rule": "A measure separates candidates only when all of them have it from the same source; no composite score; otherwise a true tie.",
            }
            ranked.append(row)
    return ranked


def explain_ranked_pair(higher: Dict[str, Any], lower: Dict[str, Any], base_dimensions: Sequence[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
    """Explain the first differing component of the saved final comparator.

    Never reuse an earlier stage's explanation or invent a differentiator from
    other available data. None means the snapshot does not establish this order.
    """
    left = higher.get("__rank_comparison_trace") or {}
    right = lower.get("__rank_comparison_trace") or {}
    if not left or not right:
        return None
    for snapshot in (left, right):
        if snapshot.get("base_dimensions") is not None and tuple(snapshot["base_dimensions"]) != tuple(base_dimensions):
            return None
    left_base, right_base = tuple(left["base_values"]), tuple(right["base_values"])
    equal = []
    if len(left_base) != len(right_base) or len(left_base) != len(base_dimensions):
        return None
    for index, (dimension, reason) in enumerate(base_dimensions):
        a, b = left_base[index], right_base[index]
        if a == b:
            equal.append(dimension)
            continue
        if a > b:
            return None
        return {"decision_dimension": dimension, "reason": reason,
                "equal_dimensions": equal, "unknown_dimensions": [],
                "comparison_evidence": {"source": "FINAL_COMPARATOR_SNAPSHOT", "component_index": index,
                                        "higher_sort_value": a, "lower_sort_value": b}}
    left_path, right_path = tuple(left["evidence_path"]), tuple(right["evidence_path"])
    for index, (a, b) in enumerate(zip(left_path, right_path)):
        if a == b:
            continue
        if a > b:
            return None
        lm, rm = left["evidence_measures"], right["evidence_measures"]
        if index >= len(lm) or index >= len(rm) or lm[index] != rm[index]:
            return None
        measure = lm[index]
        lv, rv = left["measure_values"].get(measure), right["measure_values"].get(measure)
        if not lv or not rv or lv[0] != rv[0]:
            return None
        return {"decision_dimension": measure,
                "reason": f"Shared verified evidence for {measure.replace('_', ' ')} separates these options after your own criteria were equal.",
                "equal_dimensions": equal + list(lm[:index]), "unknown_dimensions": [],
                "comparison_evidence": {"source": "FINAL_COMPARATOR_SNAPSHOT", "source_family": lv[0],
                                        "higher_comparable_value": lv[1], "lower_comparable_value": rv[1]}}
    if left_path == right_path:
        return {"decision_dimension": "true_tie", "reason": "No governed ranking difference was verified at this comparison step.",
                "equal_dimensions": equal + list(left["evidence_measures"]), "unknown_dimensions": [],
                "deterministic_display_order": True}
    return None


__all__ = ["MEASURES", "QUALITY_PARAMETERS", "measure_values", "rank_with_evidence_layer"]
