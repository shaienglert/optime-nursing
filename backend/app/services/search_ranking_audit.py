"""Read-only observations of the final comparator; never ranking authority.

Request-local capture keeps private comparator snapshots off public responses.
No questionnaire, query narrative, contact fields or family bearer token is stored.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

from app.services.regulatory_quality_layer import MEASURES

_capture = ContextVar("search_ranking_audit_capture", default=None)


@contextmanager
def capture_search_ranking_audit():
    captured = {}
    token = _capture.set(captured)
    try:
        yield captured
    finally:
        _capture.reset(token)


def observe_final_ranking(result):
    captured = _capture.get()
    if captured is not None:
        captured.update(build_search_ranking_audit(result))


def build_search_ranking_audit(result):
    rows = []
    for position, row in enumerate((result.get("results") or [])[:10], 1):
        snapshot = row.get("__rank_comparison_trace") or {}
        dimensions = snapshot.get("base_dimensions") or []
        values = snapshot.get("base_values") or []
        valid = bool(dimensions) and len(dimensions) == len(values)
        criteria = []
        if valid:
            for index, ((key, _reason), value) in enumerate(zip(dimensions, values), 1):
                criteria.append({"parameter": key, "priority": index, "value": value,
                                 "role": "ORDERED_CRITERION", "source": "FINAL_COMPARATOR_SNAPSHOT",
                                 "numeric_weight": None})
        used = snapshot.get("evidence_measures") or []
        measures = snapshot.get("measure_values") or {}
        for index, (key, _layer, better) in enumerate(MEASURES, 1):
            available = measures.get(key)
            criteria.append({"parameter": key, "priority": len(dimensions) + index if valid else None,
                             "value": available[1] if available else None,
                             "source": available[0] if available else None,
                             "role": "USED_TO_SEPARATE" if key in used else "NOT_USED_TO_SEPARATE",
                             "direction": better, "numeric_weight": None,
                             "evidence_state": "KNOWN" if available else "UNKNOWN"})
        fit = row.get("client_intent_fit") or {}
        rows.append({
            "display_position": position, "rank": row.get("rank_position"),
            "rank_display": row.get("rank_display"), "tie_status": row.get("rank_tie_status"),
            "facility_id": row.get("canonical_facility_id"), "facility_name": row.get("facility_name"),
            "must_status": row.get("must_eligibility"),
            "must_pass": fit.get("must_pass") or [], "must_fail": fit.get("must_fail") or [],
            "must_unknown": fit.get("must_unknown") or [],
            "nice_match": fit.get("nice_match") or [], "nice_unknown": fit.get("nice_unknown") or [],
            "budget_exception": row.get("budget_exception"), "budget_variance_pct": row.get("budget_variance_pct"),
            "comparison_vs_next": row.get("tie_break_explanation_vs_next"),
            "snapshot_status": "RECORDED" if valid else "UNAVAILABLE",
            "criteria": criteria,
        })
    return deepcopy({
        "schema_version": 1, "ranking_method": "ORDERED_CRITERIA_NOT_WEIGHTED_SUM",
        "numeric_weights_available": False, "top_limit": 10,
        "returned_count": len(result.get("results") or []),
        "total_candidates_scored": result.get("total_candidates_scored"),
        "pipeline_trace": result.get("decision_pipeline_trace") or {},
        "rows": rows,
    })
