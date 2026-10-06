"""Per-candidate funding explanation.

Monthly cost and one-time capital are separate facts and are never summed. Medicaid
states (approved / application pending / may qualify / unknown) stay distinct, and no
coverage is promised without verified acceptance evidence. Missing information is shown
as unknown, never as a pass or a fail.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_MEDICAID_STATES = {
    "approved": "APPROVED",
    "application pending": "APPLICATION_PENDING",
    "may qualify": "MAY_QUALIFY",
    "not eligible": "NOT_ELIGIBLE",
}


def medicaid_state(value: Any) -> str:
    return _MEDICAID_STATES.get(str(value or "").strip().lower(), "UNKNOWN")


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _links(row: Dict[str, Any]) -> List[str]:
    found: List[str] = []
    for key in ("official_website", "source_url", "primary_source_url"):
        value = str(row.get(key) or "").strip()
        if value.startswith("http") and value not in found:
            found.append(value)
    return found


def build_funding_explanation(row: Dict[str, Any], questionnaire_state: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.affordability_floor import relevant_monthly_cost

    pathway = row.get("funding_pathway") or "PRIVATE_PAY"
    amount = relevant_monthly_cost(row)
    budget = _number(questionnaire_state.get("budget"))
    budget = budget if budget and budget > 0 else None
    included = None if amount is None or budget is None else amount <= budget
    basis = "MEDICAID_HOUSEHOLD_OUT_OF_POCKET" if pathway == "MEDICAID" else "PRIVATE_PAY_PRICE"

    fee = _number(row.get("entrance_fee"))
    one_time = None
    if fee:
        capital = _number(questionnaire_state.get("availableCapital"))
        status = ("CAPITAL_NOT_PROVIDED" if capital is None
                  else "FEE_WITHIN_STATED_CAPITAL" if fee <= capital else "FEE_EXCEEDS_STATED_CAPITAL")
        one_time = {"amount": fee, "available_capital": capital, "status": status,
                    "provider_confirmation_required": True}

    state = medicaid_state(questionnaire_state.get("medicaidStatus"))
    evidence = str((row.get("verified_capabilities") or {}).get("medicaid_attributes") or "UNKNOWN").upper()
    medicaid = {"state": state, "acceptance_evidence": evidence, "coverage_promised": False}

    parts = []
    if amount is None:
        parts.append("The monthly cost for this option is not verified, so it cannot be compared with the budget.")
    else:
        parts.append(f"Monthly cost ${amount:,.0f} ({'Medicaid household out-of-pocket' if pathway == 'MEDICAID' else 'private-pay price'}); "
                     + ("within" if included else "above" if included is False else "not compared with") + " the monthly budget.")
    if one_time:
        parts.append(f"A one-time fee of ${fee:,.0f} is separate from the monthly amount: " + {
            "CAPITAL_NOT_PROVIDED": "available capital was not provided, so it is not assessed.",
            "FEE_WITHIN_STATED_CAPITAL": "it is within the stated available capital, pending provider confirmation.",
            "FEE_EXCEEDS_STATED_CAPITAL": "it exceeds the stated available capital.",
        }[one_time["status"]])
    if str(questionnaire_state.get("medicaidStatus") or "").strip() or pathway == "MEDICAID":
        parts.append(f"Medicaid status: {state.replace('_', ' ').lower()}. "
                     + ("Acceptance is verified for this community." if evidence == "YES"
                        else "Medicaid acceptance for this community is not confirmed; coverage is not promised."))
    return {
        "pathway": pathway,
        "monthly": {"amount": amount, "basis": basis, "budget": budget, "included_in_budget": included, "price_source": row.get("price_source")},
        "one_time": one_time,
        "medicaid": medicaid,
        "links": _links(row),
        "explanation": " ".join(parts),
    }
