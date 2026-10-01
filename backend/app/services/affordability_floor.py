"""Affordability floor and the Medicaid pathway CLIENT MUST.

Business rule (owner, 2026-10-01):

* The affordability floor of a search is the lowest starting monthly price among the
  communities of THAT search's candidate universe (same market, same location scope) that
  have already passed the SYSTEM MUSTs and the family's required care needs. It is computed
  after SYSTEM MUST/care and before any budget or Medicaid gate, so neither can shape it.
* When the stated budget is below that floor and Medicaid is Approved or Application
  pending, private pay cannot fund any community that meets the care needs, so the Medicaid
  pathway becomes a CLIENT MUST.
* UNKNOWN Medicaid acceptance is never PASS; it is a verification item.
* OOMNIKER may explain that the MUST narrows supply and suggest funding alternatives, but
  may not remove a CLIENT MUST without family approval.

Nothing here knows a price, a persona, or a particular care combination: the floor is read
off the rows the search produced, and "care" is the family's own HIGH/REQUIRED needs plus
the care MUSTs in their client intent.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

MEDICAID_PATHWAY_KEY = "MEDICAID_PATHWAY_REQUIRED"
MEDICAID_PURSUING_STATUSES = {"approved", "application pending"}

# Client-intent MUSTs the floor universe must have PASSED (UNKNOWN is not passed).
SYSTEM_MUST_KEYS = frozenset({"LICENSE_CURRENTLY_VALID", "LAS_VEGAS", "LAS_VEGAS_CITY_LIMITS"})
CARE_MUST_KEYS = frozenset({
    "ADL_SUPPORT_AVAILABLE",
    "MEDICATION_SUPPORT_AVAILABLE",
    "NO_FORCED_MEMORY_PLACEMENT",
    "RECOVERY_TRANSITION_COMPATIBLE",
    "REHAB_PATH_AVAILABLE",
    "SECURED_UNIT_AVAILABLE",
    "SECURE_MEMORY_CARE_CONFIRMED",
})
# Client MUSTs that are not care needs. They stay hard gates on what is shown, but they do
# not define what care costs, so they do not shape the floor. Budget and Medicaid are here
# because the floor is the thing they are compared against.
NON_CARE_CLIENT_MUST_KEYS = frozenset({
    "COUPLE_CORESIDENCE",
    "KOSHER_MEALS",
    "CONTINUUM_OF_CARE_REQUIRED",
    MEDICAID_PATHWAY_KEY,
})

# Needs-profile parameters that are not care, whatever level the family gave them.
_NON_CARE_NEED_PARAMETERS = frozenset({
    # personal / social
    "languages", "activities", "religious_cultural_services", "transportation", "gluten_free", "kosher",
    # financial access
    "medicare_attributes", "medicaid_attributes", "published_rates", "fees", "payer_information", "current_price",
    # availability / readiness
    "current_availability", "earliest_admission_date", "waiting_list",
})
_CRITICAL_LEVELS = {"REQUIRED", "HIGH"}


def _price(row: Dict[str, Any]) -> Optional[float]:
    value = row.get("starting_monthly_price")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def _care_needs(patient_profile: Dict[str, Any]) -> List[str]:
    out = []
    for need in patient_profile.get("needs") or []:
        pid = str(need.get("parameter_id") or "")
        level = str(need.get("requirement_level") or "").upper()
        if pid and level in _CRITICAL_LEVELS and pid not in _NON_CARE_NEED_PARAMETERS:
            out.append(pid)
    return out


def passes_system_and_care(row: Dict[str, Any], care_need_ids: Iterable[str], gate_keys: Iterable[str]) -> bool:
    """True only when every SYSTEM/care MUST passed and every critical care need MATCHED.

    A row with any of them UNKNOWN has not passed; it is not evidence of what care costs.
    """
    if str(row.get("eligibility_status") or "").upper() == "INELIGIBLE":
        return False
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    passed = set(fit.get("must_pass") or [])
    if any(key not in passed for key in gate_keys):
        return False
    matched = {str(item.get("parameter_id") or "") for item in row.get("matched_needs") or [] if isinstance(item, dict)}
    return all(pid in matched for pid in care_need_ids)


def compute_affordability_floor(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], patient_profile: Dict[str, Any]) -> Dict[str, Any]:
    intent_keys = [str(m.get("key") or "") for m in client_intent.get("must_haves") or []]
    gate_keys = [key for key in intent_keys if key in SYSTEM_MUST_KEYS or key in CARE_MUST_KEYS]
    care_need_ids = _care_needs(patient_profile)
    qualified = [row for row in rows if passes_system_and_care(row, care_need_ids, gate_keys)]
    priced = [(price, row) for row in qualified if (price := _price(row)) is not None]
    floor: Dict[str, Any] = {
        "basis": "LOWEST_PRICE_AMONG_SEARCH_CANDIDATES_PASSING_SYSTEM_AND_CARE_MUSTS",
        "candidate_universe_count": len(rows),
        "system_and_care_must_keys": gate_keys,
        "care_need_parameters": care_need_ids,
        "qualified_count": len(qualified),
        "qualified_priced_count": len(priced),
        "floor_monthly_price": None,
        "floor_canonical_facility_id": None,
    }
    if priced:
        price, row = min(priced, key=lambda pair: (pair[0], str(pair[1].get("canonical_facility_id") or "")))
        floor["floor_monthly_price"] = price
        floor["floor_canonical_facility_id"] = row.get("canonical_facility_id")
    return floor


def _budget(questionnaire_state: Dict[str, Any]) -> Optional[float]:
    value = questionnaire_state.get("budget")
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def apply_medicaid_affordability_rule(
    rows: List[Dict[str, Any]],
    client_intent: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    patient_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute the floor for this search and, when the rule holds, add the Medicaid CLIENT MUST.

    Returns the decision record (also stored on client_intent["affordability_floor"]).
    The caller must re-evaluate client intent fit when ``promoted`` is True.
    """
    floor = compute_affordability_floor(rows, client_intent, patient_profile)
    medicaid_status = str(questionnaire_state.get("medicaidStatus") or "").strip().lower()
    budget = _budget(questionnaire_state)
    floor_price = floor["floor_monthly_price"]
    already = any(str(m.get("key") or "") == MEDICAID_PATHWAY_KEY for m in client_intent.get("must_haves") or [])
    pursuing = medicaid_status in MEDICAID_PURSUING_STATUSES
    below_floor = budget is not None and floor_price is not None and budget < floor_price

    if not pursuing:
        outcome = "NOT_APPLICABLE_MEDICAID_NOT_PURSUED"
    elif budget is None:
        outcome = "NOT_DETERMINED_NO_BUDGET"
    elif floor_price is None:
        # No community in this search has passed the care needs with a known price, so
        # affordability cannot be compared. Not a reason to invent a MUST; it is a gap the
        # explanation layer must state.
        outcome = "NOT_DETERMINED_NO_QUALIFIED_PRICE"
    elif below_floor:
        outcome = "MEDICAID_PATHWAY_CLIENT_MUST"
    else:
        outcome = "PRIVATE_PAY_REACHABLE"

    promoted = outcome == "MEDICAID_PATHWAY_CLIENT_MUST" and not already
    record = {
        **floor,
        "budget": budget,
        "medicaid_status": questionnaire_state.get("medicaidStatus"),
        "outcome": outcome,
        "medicaid_pathway_client_must": outcome == "MEDICAID_PATHWAY_CLIENT_MUST",
        "removal_policy": "A CLIENT MUST may be explained and alternatives suggested; it is removed only with family approval.",
    }
    if promoted:
        client_intent.setdefault("must_haves", []).append({
            "key": MEDICAID_PATHWAY_KEY,
            "reason": (
                f"The ${budget:,.0f} budget is below ${floor_price:,.0f}, the lowest price among communities "
                "in this search that meet the care needs, and Medicaid is "
                f"{str(questionnaire_state.get('medicaidStatus') or '').lower()}; only a Medicaid pathway can fund a placement."
            ),
            "verification": "verified Medicaid acceptance (waiver/HCBS or Medicaid-certified bed); UNKNOWN is not a pass",
            "origin": "AFFORDABILITY_FLOOR_RULE",
            "client_must": True,
            "removable_only_with_family_approval": True,
        })
        for need in patient_profile.get("needs") or []:
            if need.get("parameter_id") == "medicaid_attributes":
                need["requirement_level"] = "HIGH"
                need["acceptable_values"] = ["YES"]
                need["need_text"] = "Medicaid pathway is a CLIENT MUST: the budget is below the care-qualified price floor of this search"
                need["promoted_by"] = "AFFORDABILITY_FLOOR_RULE"
    client_intent["affordability_floor"] = record
    return {**record, "promoted": promoted}


# ---- Funding pathway (owner, 2026-10-01) ------------------------------------------------
# The funding pathway is decided before the final affordability gate, and the budget is
# compared with the cost the household actually pays under that pathway:
#   PRIVATE_PAY                       -> private-pay price
#   MEDICAID (CLIENT MUST active)     -> verified household out-of-pocket under Medicaid
# An unknown relevant cost is EVIDENCE_PENDING (never PASS, never FAIL). Nothing is
# inferred from the private-pay price.
MEDICAID_OOP_PARAMETER = "medicaid_household_out_of_pocket"
FUNDING_EVIDENCE_PARAMETER_IDS = frozenset({MEDICAID_OOP_PARAMETER})


def _money(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def apply_funding_pathway(rows: List[Dict[str, Any]], client_intent: Dict[str, Any]) -> str:
    keys = {str(m.get("key") or "") for m in client_intent.get("must_haves") or []}
    pathway = "MEDICAID" if MEDICAID_PATHWAY_KEY in keys else "PRIVATE_PAY"
    client_intent["funding_pathway"] = pathway
    for row in rows:
        row["funding_pathway"] = pathway
        if pathway == "MEDICAID":
            row["relevant_monthly_cost"] = _money((row.get("verified_capabilities") or {}).get(MEDICAID_OOP_PARAMETER))
            row["relevant_cost_basis"] = "MEDICAID_HOUSEHOLD_OUT_OF_POCKET"
        else:
            row["relevant_monthly_cost"] = _money(row.get("starting_monthly_price"))
            row["relevant_cost_basis"] = "PRIVATE_PAY_PRICE"
    return pathway


def relevant_monthly_cost(row: Dict[str, Any]) -> Optional[float]:
    """The cost the budget is compared with for this row (see apply_funding_pathway)."""
    if row.get("funding_pathway") == "MEDICAID":
        return row.get("relevant_monthly_cost")
    # Private pay: always the current price (later stages may complete it, e.g. a couple's
    # second-resident fee), never a stale copy.
    return _money(row.get("starting_monthly_price"))


__all__ = [
    "MEDICAID_OOP_PARAMETER",
    "FUNDING_EVIDENCE_PARAMETER_IDS",
    "apply_funding_pathway",
    "relevant_monthly_cost",
    "MEDICAID_PATHWAY_KEY",
    "SYSTEM_MUST_KEYS",
    "CARE_MUST_KEYS",
    "NON_CARE_CLIENT_MUST_KEYS",
    "apply_medicaid_affordability_rule",
    "compute_affordability_floor",
    "passes_system_and_care",
]
