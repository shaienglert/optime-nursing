from __future__ import annotations
from typing import Any, Dict, List, Optional

IMMUTABLE_SYSTEM_MUST='SYSTEM_MUST'
CLIENT_MUST='CLIENT_MUST'
PREFERENCE='PREFERENCE'

# What Oomniker may never offer to relax: legal/system rules and the family's care needs.
_IMMUTABLE_AUTHORITIES = {"SYSTEM_MUST", "CARE_MUST", "CARE_NEED"}
# A CLIENT MUST can be offered for reconsideration only when the Structured Profile has an
# answer that expresses the relaxed choice; otherwise Oomniker can only explain it.
CLIENT_MUST_LEVERS = {
    "KOSHER_MEALS": "humanIntelligenceV2.culturalProfile.kosherRequirements",
    "CONTINUUM_OF_CARE_REQUIRED": "humanIntelligenceV2.futureCareProfile.continuumOfCarePreference",
    "MEDICAID_PATHWAY_REQUIRED": "medicaidStatus",
}


def analyze_oomniker(profile:dict[str,Any], candidates:list[dict[str,Any]], *, filtered_universe:list[dict[str,Any]]|None=None, decision_context:Optional[Dict[str,Any]]=None)->dict[str,Any]:
    """Advisory AI boundary: maximize viable choice only after SYSTEM MUST filtering.

    With decision_context (canonical profile, client intent, the full candidate ledger and
    the mechanical funnel) the advice is a counterfactual over the WHOLE candidate universe
    of this search: for each relaxable constraint, how many more communities would become
    recommendable if that one constraint alone changed. SYSTEM MUSTs and care needs are
    never offered; a CLIENT MUST is offered only as a question the family must approve.
    """
    if decision_context is not None:
        return _counterfactual(profile, candidates, decision_context)
    universe=list(filtered_universe if filtered_universe is not None else candidates)
    constraints=profile.get('constraints') if isinstance(profile.get('constraints'),list) else []
    suggestions=[]
    immutable=[]
    for constraint in constraints:
        if not isinstance(constraint,dict): continue
        level=str(constraint.get('authority') or constraint.get('requirement_level') or PREFERENCE).upper()
        key=str(constraint.get('parameter') or constraint.get('parameter_id') or '')
        if level==IMMUTABLE_SYSTEM_MUST:
            immutable.append(key); continue
        matching=sum(1 for row in universe if key in set(row.get('matched_parameter_ids') or []))
        lost=max(0,len(universe)-matching)
        if not lost: continue
        if level==CLIENT_MUST:
            suggestions.append({'parameter':key,'authority':CLIENT_MUST,'action':'ASK_CLIENT_TO_RECONSIDER','requires_client_approval':True,'options_preserved':matching,'additional_options_if_relaxed':lost,'may_auto_change':False})
        else:
            suggestions.append({'parameter':key,'authority':PREFERENCE,'action':'RECOMMEND_TRANSPARENT_ALTERNATIVE','requires_client_approval':True,'options_preserved':matching,'additional_options_if_relaxed':lost,'may_auto_change':False})
    budget=profile.get('budget')
    if isinstance(budget,(int,float)) and budget>0:
        tolerance=sum(1 for r in universe if isinstance(r.get('starting_monthly_price'),(int,float)) and budget<r['starting_monthly_price']<=budget*1.10)
        if tolerance: suggestions.append({'parameter':'budget','authority':PREFERENCE,'action':'RECOMMEND_WITHIN_APPROVED_10_PERCENT','requires_client_approval':True,'additional_options_if_relaxed':tolerance,'may_auto_change':False})
    suggestions.sort(key=lambda x:(-int(x.get('additional_options_if_relaxed') or 0),str(x.get('parameter'))))
    return {'status':'AI_ADVISOR_WITH_GOVERNED_BOUNDARIES','system_must_immutable':immutable,'input_universe':'POST_SYSTEM_MUST_FILTER_ONLY','profile_mutated':False,'suggestions':suggestions,'candidate_count':len(universe)}


def _counterfactual(profile: Dict[str, Any], shown: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.decision_funnel import blocking_reasons

    ledger = [item for item in context.get("ledger") or [] if isinstance(item, dict)]
    intent = context.get("client_intent") if isinstance(context.get("client_intent"), dict) else {}
    budget = profile.get("budget") if isinstance(profile.get("budget"), (int, float)) and not isinstance(profile.get("budget"), bool) else None
    per_row = [(item, blocking_reasons(item, budget)) for item in ledger]
    recommendable = sum(1 for _, reasons in per_row if not reasons)

    by_reason: Dict[tuple, List[Dict[str, Any]]] = {}
    immutable: Dict[str, int] = {}
    pending_only: Dict[str, int] = {}
    for item, reasons in per_row:
        if not reasons:
            continue
        verified = [r for r in reasons if r["kind"] != "UNKNOWN"]
        unknown = [r for r in reasons if r["kind"] == "UNKNOWN"]
        for r in reasons:
            if r["authority"] in _IMMUTABLE_AUTHORITIES:
                immutable[r["reason"]] = immutable.get(r["reason"], 0) + 1
        if not verified:
            names = {r["reason"] for r in unknown}
            for name in names:
                entry = pending_only.setdefault(name, {"waiting": 0, "only": 0})
                entry["waiting"] += 1
                if len(names) == 1:
                    entry["only"] += 1
            continue
        distinct = {(r["reason"], r["authority"]) for r in verified}
        if len(distinct) == 1 and not unknown:
            by_reason.setdefault(next(iter(distinct)), []).append(item)

    suggestions: List[Dict[str, Any]] = []
    for (reason, authority), items in by_reason.items():
        if authority in _IMMUTABLE_AUTHORITIES:
            continue
        entry = {
            "parameter": reason,
            "authority": authority,
            "additional_options_if_relaxed": len(items),
            "requires_client_approval": True,
            "may_auto_change": False,
            "basis": "COUNTERFACTUAL_OVER_FULL_CANDIDATE_UNIVERSE",
        }
        if authority == "CLIENT_BUDGET":
            prices = sorted(i["price"] for i in items if isinstance(i.get("price"), (int, float)))
            entry["action"] = "SHOW_BUDGET_NEEDED"
            if prices:
                entry["lowest_price_unlocked"] = prices[0]
                entry["budget_needed_for_first_option"] = round(prices[0] / 1.10)
        elif authority == "CLIENT_MUST" and reason not in CLIENT_MUST_LEVERS:
            entry["action"] = "EXPLAIN_NARROWING"
            entry["profile_lever"] = None
            entry["note"] = "This requirement narrows the choice; the interview has no answer that relaxes it, so it is explained, not offered."
        elif authority == "CLIENT_MUST":
            entry["action"] = "ASK_CLIENT_TO_RECONSIDER"
            entry["profile_lever"] = CLIENT_MUST_LEVERS[reason]
            entry["note"] = "A CLIENT MUST is removed only with the family's approval."
            if reason == "MEDICAID_PATHWAY_REQUIRED":
                entry["note"] = "Private pay is below the care-qualified price floor; these communities do not accept Medicaid. Funding alternatives can be explained, the requirement is not removed without approval."
        else:
            entry["action"] = "RECOMMEND_TRANSPARENT_ALTERNATIVE"
        suggestions.append(entry)
    scope = context.get("location_scope") if isinstance(context.get("location_scope"), dict) else {}
    offer = scope.get("expansion_offer") if isinstance(scope.get("expansion_offer"), dict) else None
    if offer:
        suggestions.append({
            "parameter": "maximum_distance_miles",
            "authority": "CLIENT_LIMIT",
            "action": "OFFER_RADIUS_EXPANSION",
            "proposed_miles": offer.get("miles"),
            "additional_candidates_before_requirement_checks": offer.get("additional_count"),
            "requires_client_approval": True,
            "may_auto_change": False,
            "basis": "LOCATION_SCOPE_EXPANSION_OFFER",
        })
    for reason, counts in sorted(pending_only.items(), key=lambda kv: (-kv[1]["waiting"], kv[0])):
        suggestions.append({
            "parameter": reason,
            "authority": "EVIDENCE",
            "action": "VERIFY_WITH_COMMUNITIES",
            "candidates_waiting_on_this_evidence": counts["waiting"],
            "candidates_waiting_only_on_this_evidence": counts["only"],
            "requires_client_approval": False,
            "may_auto_change": False,
            "basis": "UNKNOWN_IS_A_VERIFICATION_ITEM",
        })
    suggestions.sort(key=lambda x: (-int(x.get("additional_options_if_relaxed") or x.get("candidates_waiting_on_this_evidence") or 0), str(x.get("parameter"))))
    funnel = context.get("funnel") if isinstance(context.get("funnel"), dict) else {}
    return {
        "status": "AI_ADVISOR_WITH_GOVERNED_BOUNDARIES",
        "input_universe": "FULL_CANDIDATE_LEDGER_OF_THIS_SEARCH",
        "candidate_universe_count": len(ledger),
        "recommendable_count": recommendable,
        "shown_count": len(shown),
        "client_musts": [str(m.get("key") or "") for m in intent.get("must_haves") or []],
        "immutable_constraints_blocking": dict(sorted(immutable.items())),
        "system_must_immutable": sorted(k for k in immutable),
        "zero_result_classification": funnel.get("zero_result_classification"),
        "zeroing_parameter": funnel.get("zeroing_parameter"),
        "profile_mutated": False,
        "suggestions": suggestions,
        "candidate_count": len(ledger),
    }
