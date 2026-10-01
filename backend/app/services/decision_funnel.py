"""Mechanical decision funnel and zero-result classification.

Owner rule (2026-10-01): a zero result is neither a pass nor a fail by itself. Every search
reports, mechanically, how many communities entered the market universe and how many left
at each stage -- SYSTEM MUST, care, CLIENT MUST, verified budget, location, UNKNOWN
evidence -- and which parameter took the count to zero. The classification is derived from
that trace, so a CORRECT_ZERO cannot hide an earlier engine bug: if the stages do not
reconcile, or candidates that cleared every gate are not shown, it is ENGINE_FAILURE.

Classes (zero results only):
  CORRECT_ZERO      every candidate was removed by verified evidence or a stated client
                    limit (radius, budget against a verified price).
  EVIDENCE_PENDING  the last candidates were held only by UNKNOWN evidence on a MUST.
  ENGINE_FAILURE    the trace does not reconcile, recommendable candidates were lost, or a
                    requested MUST has no evidence source in this market (readiness gap).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.services.affordability_floor import CARE_MUST_KEYS, NON_CARE_CLIENT_MUST_KEYS, SYSTEM_MUST_KEYS, relevant_monthly_cost

BUDGET_TOLERANCE = 0.10
# Semantic keys that restate a canonical fact; the funnel reads the fact itself.
_BUDGET_KEYS = {"SEMANTIC_BUDGET_VERIFICATION", "BUDGET_FIT"}
_NON_CARE_NEEDS = {
    "languages", "activities", "religious_cultural_services", "transportation", "gluten_free", "kosher",
    "medicare_attributes", "medicaid_attributes", "published_rates", "fees", "payer_information", "current_price",
    "current_availability", "earliest_admission_date", "waiting_list",
}


def ledger_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compact per-candidate record of every in-scope row after the MUST gate."""
    out = []
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        out.append({
            "canonical_facility_id": row.get("canonical_facility_id"),
            "eligibility_status": row.get("eligibility_status"),
            "unmet_critical_needs": [
                str(item.get("parameter_id") or "")
                for item in row.get("unmet_verified_needs") or []
                if str(item.get("requirement_level") or "").upper() in {"REQUIRED", "HIGH"}
            ],
            "must_fail": list(fit.get("must_fail") or []),
            "must_unknown": list(fit.get("must_unknown") or []),
            # The cost the budget is compared with under the funding pathway.
            "price": relevant_monthly_cost(row),
            "cost_basis": row.get("relevant_cost_basis") or "PRIVATE_PAY_PRICE",
        })
    return out


def merge_late_fit(ledger: List[Dict[str, Any]], rows: Iterable[Dict[str, Any]]) -> None:
    """Later stages (semantic requirements, combined care) re-evaluate the rows they see."""
    by_id = {item["canonical_facility_id"]: item for item in ledger}
    for row in rows:
        item = by_id.get(row.get("canonical_facility_id"))
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        if item is not None:
            if fit:
                item["must_fail"] = list(fit.get("must_fail") or [])
                item["must_unknown"] = list(fit.get("must_unknown") or [])
            item["price"] = relevant_monthly_cost(row)


def _unknown_cost_reason(item: Dict[str, Any]) -> str:
    return "medicaid_household_out_of_pocket_unknown" if item.get("cost_basis") == "MEDICAID_HOUSEHOLD_OUT_OF_POCKET" else "current_price_unknown"


def _key_class(key: str) -> str:
    if key in SYSTEM_MUST_KEYS:
        return "SYSTEM_MUST"
    if key in CARE_MUST_KEYS:
        return "CARE_MUST"
    if key in _BUDGET_KEYS:
        return "BUDGET"
    return "CLIENT_MUST"


def _remove(survivors: List[Dict[str, Any]], stage: str, reasons_for, stages: List[Dict[str, Any]], order: List[str]) -> List[Dict[str, Any]]:
    """Apply one stage; attribute each removal to the first reason in declared order."""
    removed_by: Dict[str, int] = {}
    kept: List[Dict[str, Any]] = []
    zeroing_reason: Optional[str] = None
    for item in survivors:
        reasons = reasons_for(item)
        if reasons:
            first = min(reasons, key=lambda r: (order.index(r) if r in order else len(order), r))
            removed_by[first] = removed_by.get(first, 0) + 1
        else:
            kept.append(item)
    if survivors and not kept and removed_by:
        # The reason that removed the last survivors when applied one key at a time.
        remaining = list(survivors)
        for reason in sorted(removed_by, key=lambda r: (order.index(r) if r in order else len(order), r)):
            remaining = [item for item in remaining if reason not in reasons_for(item)]
            if not remaining:
                zeroing_reason = reason
                break
    stages.append({"stage": stage, "entered": len(survivors), "removed": len(survivors) - len(kept), "removed_by": removed_by, "remaining": len(kept), "zeroing_parameter": zeroing_reason})
    return kept


def build_funnel(
    *,
    catalog: Dict[str, Any],
    location_scope: Dict[str, Any],
    ledger: List[Dict[str, Any]],
    must_order: List[str],
    budget: Optional[float],
    shown_count: int,
    requested_must_coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stages: List[Dict[str, Any]] = []
    universe = int(catalog.get("market_universe_count") or 0)
    excluded_by = catalog.get("excluded_ids_by_parameter") or {}
    catalog_removed: Dict[str, int] = {}
    seen: set = set()
    for parameter in sorted(excluded_by):
        fresh = [cid for cid in excluded_by[parameter] if cid not in seen]
        seen.update(fresh)
        if fresh:
            catalog_removed[parameter] = len(fresh)
    discovered = universe - len(seen)
    stages.append({"stage": "MARKET_UNIVERSE", "remaining": universe})
    stages.append({
        "stage": "REQUIRED_NEED_VERIFIED_NO_AT_RETRIEVAL", "entered": universe, "removed": len(seen),
        "removed_by": catalog_removed, "remaining": discovered,
        "zeroing_parameter": (sorted(catalog_removed)[-1] if discovered == 0 and catalog_removed else None),
    })
    scored = int(catalog.get("scored_count") if catalog.get("scored_count") is not None else discovered)
    in_scope = int(catalog.get("in_scope_count") if catalog.get("in_scope_count") is not None else len(ledger))
    location_removed = scored - in_scope
    stages.append({
        "stage": "LOCATION_RADIUS", "entered": scored, "removed": location_removed,
        "removed_by": {"distance_beyond_radius": location_removed} if location_removed else {},
        "remaining": in_scope, "applied": bool(location_scope.get("applied")),
        "zeroing_parameter": "distance_beyond_radius" if scored and not in_scope else None,
    })

    reconciliation: List[str] = []
    if scored != discovered:
        reconciliation.append(f"scored {scored} != discovered {discovered}")
    if len(ledger) != in_scope:
        reconciliation.append(f"ledger {len(ledger)} != in-scope {in_scope}")

    survivors = list(ledger)
    survivors = _remove(survivors, "CARE_NEED_VERIFIED_GAP", lambda i: [p for p in i["unmet_critical_needs"] if p not in _NON_CARE_NEEDS] if i["eligibility_status"] == "INELIGIBLE" else [], stages, [])
    survivors = _remove(survivors, "CLIENT_NEED_VERIFIED_GAP", lambda i: list(i["unmet_critical_needs"]) if i["eligibility_status"] == "INELIGIBLE" else [], stages, [])
    for klass in ("SYSTEM_MUST", "CARE_MUST", "CLIENT_MUST"):
        survivors = _remove(survivors, f"{klass}_VERIFIED_FAIL", lambda i, k=klass: [key for key in i["must_fail"] if _key_class(key) == k], stages, must_order)
    ceiling = budget * (1 + BUDGET_TOLERANCE) if budget else None
    survivors = _remove(
        survivors, "BUDGET_VERIFIED_PRICE_ABOVE_LIMIT",
        lambda i: ["current_price_above_budget_plus_10pct"] if (ceiling is not None and i["price"] is not None and i["price"] > ceiling) or any(_key_class(k) == "BUDGET" for k in i["must_fail"]) else [],
        stages, [],
    )
    survivors = _remove(
        survivors, "MUST_EVIDENCE_UNKNOWN",
        lambda i: [key for key in i["must_unknown"] if _key_class(key) != "BUDGET"]
        + ([_unknown_cost_reason(i)] if ceiling is not None and i["price"] is None else [])
        + (["total_monthly_cost_unverified"] if i["price"] is not None and any(_key_class(k) == "BUDGET" for k in i["must_unknown"]) else []),
        stages, must_order + ["current_price_unknown", "medicaid_household_out_of_pocket_unknown", "total_monthly_cost_unverified"],
    )
    recommendable = len(survivors)
    recommendable_ids = sorted(str(item.get("canonical_facility_id") or "") for item in survivors)
    stages.append({"stage": "RECOMMENDABLE", "remaining": recommendable})
    stages.append({"stage": "SHOWN", "remaining": shown_count})

    readiness_gaps = sorted(key for key, item in (requested_must_coverage or {}).items() if item.get("status") != "COVERED")
    zero_stage = next((s for s in stages if s.get("remaining") == 0 and s["stage"] not in {"RECOMMENDABLE", "SHOWN"}), None)
    if shown_count > 0:
        classification, reason = "NOT_ZERO", None
    elif reconciliation:
        classification, reason = "ENGINE_FAILURE", "TRACE_DOES_NOT_RECONCILE"
    elif readiness_gaps:
        classification, reason = "ENGINE_FAILURE", "MARKET_EVIDENCE_COVERAGE_GAP"
    elif recommendable > 0:
        classification, reason = "ENGINE_FAILURE", "RECOMMENDABLE_CANDIDATES_NOT_SHOWN"
    elif zero_stage is None:
        classification, reason = "ENGINE_FAILURE", "ZERO_WITHOUT_A_ZEROING_STAGE"
    elif zero_stage["stage"] == "MUST_EVIDENCE_UNKNOWN":
        classification, reason = "EVIDENCE_PENDING", zero_stage["stage"]
    else:
        classification, reason = "CORRECT_ZERO", zero_stage["stage"]
    return {
        "version": "decision-funnel-v1",
        "stages": stages,
        "recommendable_count": recommendable,
        "recommendable_ids": recommendable_ids,
        "shown_count": shown_count,
        "zero_result_classification": classification,
        "zero_result_reason": reason,
        "zeroing_stage": zero_stage["stage"] if zero_stage and shown_count == 0 else None,
        "zeroing_parameter": zero_stage.get("zeroing_parameter") if zero_stage and shown_count == 0 else None,
        "reconciliation_errors": reconciliation,
        "readiness_gaps": readiness_gaps,
    }


def blocking_reasons(item: Dict[str, Any], budget: Optional[float]) -> List[Dict[str, str]]:
    """Every reason one candidate is not recommendable, with its authority class --
    the same classification the funnel uses. Empty list = recommendable."""
    reasons: List[Dict[str, str]] = []
    if item.get("eligibility_status") == "INELIGIBLE":
        for parameter in item.get("unmet_critical_needs") or []:
            reasons.append({"reason": parameter, "authority": "CLIENT_NEED" if parameter in _NON_CARE_NEEDS else "CARE_NEED", "kind": "VERIFIED_GAP"})
    for key in item.get("must_fail") or []:
        klass = _key_class(key)
        if klass != "BUDGET":
            reasons.append({"reason": key, "authority": klass, "kind": "VERIFIED_FAIL"})
    ceiling = budget * (1 + BUDGET_TOLERANCE) if budget else None
    over = (ceiling is not None and item.get("price") is not None and item["price"] > ceiling) or any(_key_class(k) == "BUDGET" for k in item.get("must_fail") or [])
    if over:
        reasons.append({"reason": "budget", "authority": "CLIENT_BUDGET", "kind": "VERIFIED_FAIL"})
    for key in item.get("must_unknown") or []:
        if _key_class(key) != "BUDGET":
            reasons.append({"reason": key, "authority": _key_class(key), "kind": "UNKNOWN"})
    if ceiling is not None and item.get("price") is None:
        reasons.append({"reason": "medicaid_household_out_of_pocket" if item.get("cost_basis") == "MEDICAID_HOUSEHOLD_OUT_OF_POCKET" else "current_price", "authority": "CLIENT_BUDGET", "kind": "UNKNOWN"})
    elif item.get("price") is not None and not over and any(_key_class(k) == "BUDGET" for k in item.get("must_unknown") or []):
        reasons.append({"reason": "total_monthly_cost", "authority": "CLIENT_BUDGET", "kind": "UNKNOWN"})
    return reasons


__all__ = ["blocking_reasons", "build_funnel", "ledger_rows", "merge_late_fit"]
