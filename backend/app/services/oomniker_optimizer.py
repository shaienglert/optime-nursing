from __future__ import annotations
from typing import Any
IMMUTABLE_SYSTEM_MUST = "SYSTEM_MUST"
CLIENT_MUST = "CLIENT_MUST"
PREFERENCE = "PREFERENCE"
_IMMUTABLE_AUTHORITIES = {"SYSTEM_MUST", "CARE_MUST", "CARE_NEED"}

def analyze_oomniker(profile: dict, candidates: list[dict], *, filtered_universe=None, decision_context=None) -> dict:
    """Explain narrowing; offer measured NTH alternatives only, never relax a MUST."""
    if decision_context is not None:
        return _counterfactual(profile, candidates, decision_context)
    universe = list(filtered_universe if filtered_universe is not None else candidates)
    immutable = [str(c.get("parameter") or c.get("parameter_id") or "") for c in profile.get("constraints") or []
                 if isinstance(c, dict) and str(c.get("authority") or c.get("requirement_level") or "").upper() in _IMMUTABLE_AUTHORITIES]
    # Absence from a legacy match list is UNKNOWN, not a lost option.
    return {"status": "AI_ADVISOR_WITH_GOVERNED_BOUNDARIES", "system_must_immutable": immutable,
            "input_universe": "POST_SYSTEM_MUST_FILTER_ONLY", "profile_mutated": False,
            "suggestions": [], "candidate_count": len(universe)}

def _counterfactual(profile: dict, shown: list[dict], context: dict) -> dict:
    from app.services.decision_funnel import blocking_reasons
    ledger = [item for item in context.get("ledger") or [] if isinstance(item, dict)]
    intent = context.get("client_intent") or {}
    budget = profile.get("budget")
    if not isinstance(budget, (int, float)) or isinstance(budget, bool):
        budget = None
    recommendable, immutable, constraints, pending_only = 0, {}, {}, {}
    for item in ledger:
        reasons = blocking_reasons(item, budget)
        if not reasons:
            recommendable += 1
        verified = [r for r in reasons if r["kind"] != "UNKNOWN"]
        unknown = {r["reason"] for r in reasons if r["kind"] == "UNKNOWN"}
        distinct = {(r["reason"], r["authority"]) for r in verified}
        for reason, authority in distinct:
            entry = constraints.setdefault(reason, {"parameter": reason, "authority": authority, "blocked_count": 0,
                                                    "sole_verified_blocker_count": 0, "may_relax": False})
            entry["blocked_count"] += 1
            if len(distinct) == 1 and not unknown:
                entry["sole_verified_blocker_count"] += 1
            if authority in _IMMUTABLE_AUTHORITIES:
                immutable[reason] = immutable.get(reason, 0) + 1
        if not verified:
            for reason in unknown:
                entry = pending_only.setdefault(reason, {"waiting": 0, "only": 0})
                entry["waiting"] += 1
                entry["only"] += int(len(unknown) == 1)
    measured = context.get("preference_analysis") or {}
    suggestions = []
    for item in measured.get("suggestions") or []:
        ids = {str(row.get("canonical_facility_id") or "") for row in item.get("candidates") or []}
        if (item.get("authority") == PREFERENCE and item.get("action") == "OFFER_PREFERENCE_ALTERNATIVE"
                and item.get("new_recommendation_count") == len(ids) and len(ids) >= 2 and "" not in ids
                and item.get("requires_client_approval") is True and item.get("may_auto_change") is False):
            suggestions.append(item)
    # Present at most three different changes; effects are alternatives, not additive.
    best_by_parameter = {}
    for suggestion in sorted(suggestions, key=lambda item: -item["new_recommendation_count"]):
        best_by_parameter.setdefault(suggestion["parameter"], suggestion)
    suggestions = list(best_by_parameter.values())[:3]
    for reason, counts in sorted(pending_only.items()):
        if counts["waiting"] < 2:
            continue
        suggestions.append({"parameter": reason, "authority": "EVIDENCE", "action": "VERIFY_WITH_COMMUNITIES",
                            "candidates_waiting_on_this_evidence": counts["waiting"],
                            "candidates_waiting_only_on_this_evidence": counts["only"],
                            "requires_client_approval": False, "may_auto_change": False,
                            "basis": "UNKNOWN_IS_A_VERIFICATION_ITEM"})
    funnel = context.get("funnel") or {}
    return {"status": "AI_ADVISOR_WITH_GOVERNED_BOUNDARIES", "input_universe": "FULL_CANDIDATE_LEDGER_OF_THIS_SEARCH",
            "candidate_universe_count": len(ledger), "recommendable_count": recommendable, "shown_count": min(5, len(shown)),
            "client_musts": [str(m.get("key") or "") for m in intent.get("must_haves") or []],
            "immutable_constraints_blocking": dict(sorted(immutable.items())), "system_must_immutable": sorted(immutable),
            "constraint_impacts": sorted(constraints.values(), key=lambda item: (-item["blocked_count"], item["parameter"])),
            "preference_analysis": measured, "zero_result_classification": funnel.get("zero_result_classification"),
            "zeroing_parameter": funnel.get("zeroing_parameter"), "profile_mutated": False,
            "suggestions": suggestions, "candidate_count": len(ledger)}
