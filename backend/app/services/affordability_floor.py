"""Monthly starting-price filtering. Owner 2026-10-05: insurance is outside search.
See docs/MONTHLY_STARTING_PRICE_POLICY.md; legacy wire helpers retain names only.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
from math import isfinite

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
    "POST_HOSPITAL_REHAB_PROGRAM",
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
    "REQUIRED_LANGUAGE_SUPPORT",
    "REQUIRED_ACTIVITIES",
    "CURRENT_AVAILABILITY_FOR_URGENT_MOVE",
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
    client_intent["must_haves"] = [m for m in client_intent.get("must_haves", []) if m.get("key") != MEDICAID_PATHWAY_KEY]
    record = {**floor, "budget": _budget(questionnaire_state), "outcome": "INSURANCE_OUTSIDE_SEARCH", "medicaid_pathway_client_must": False}
    client_intent["affordability_floor"] = record
    return {**record, "promoted": False}


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
    return number if isfinite(number) and number >= 0 else None


def apply_funding_pathway(rows: List[Dict[str, Any]], client_intent: Dict[str, Any]) -> str:
    pathway = "PRIVATE_PAY"  # monthly starting-price search only
    client_intent["funding_pathway"] = pathway
    for row in rows:
        row["funding_pathway"] = pathway
        row["relevant_monthly_cost"] = relevant_monthly_cost(row)
        row["relevant_cost_basis"] = "MONTHLY_STARTING_PRICE"
    return pathway


def relevant_monthly_cost(row: Dict[str, Any]) -> Optional[float]:
    """The cost the budget is compared with for this row (see apply_funding_pathway)."""
    rooms = [room.get("base_price") for room in row.get("room_pricing_options") or [] if isinstance(room, dict)]
    prices = [price for value in rooms if (price := _money(value)) is not None and price > 0]
    return min(prices) if prices else _money(row.get("starting_monthly_price"))


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
