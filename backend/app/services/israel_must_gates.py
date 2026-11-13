"""Israeli MUST gates, evaluated by the shared client-intent engine.

The Israeli lists are an outreach catalog. A gate is decided only by what the
facility itself filled in when it registered (basis FACILITY_SUPPLIED); list
data and license type decide nothing. Anything else is PENDING, never PASS or
FAIL.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FUNCTIONAL_LEVEL_KEY = "IL_FUNCTIONAL_LEVEL"
MOH_CODE_AGREEMENT_KEY = "IL_MOH_CODE_AGREEMENT"

FUNCTIONAL_LEVELS = {"INDEPENDENT", "FRAIL", "NURSING", "COGNITIVE_FRAIL"}
FUNDING_PATHWAYS = {"MOH_CODE", "WELFARE_ASSISTANCE", "PRIVATE"}

# Wards as Israeli lists name them -> the functional level each ward serves.
DEPARTMENT_LEVELS = {
    "עצמאיים": "INDEPENDENT",
    "תשושים": "FRAIL",
    "סיעודית": "NURSING",
    "סיעודי": "NURSING",
    "תשושי נפש": "COGNITIVE_FRAIL",
}

PASS, FAIL, PENDING = "PASS", "FAIL", "PENDING"


def _fact(row: Dict[str, Any], block: str, name: str) -> Dict[str, Any]:
    section = row.get(block) if isinstance(row.get(block), dict) else {}
    fact = section.get(name) if isinstance(section.get(name), dict) else {}
    return fact


def _stated(fact: Dict[str, Any]) -> bool:
    return str(fact.get("status") or "").upper() == "STATED" and fact.get("value") not in (None, [], "")


def _facility_supplied(fact: Dict[str, Any]) -> bool:
    return _stated(fact) and str(fact.get("basis")) == "FACILITY_SUPPLIED"


def _levels_from(row: Dict[str, Any]) -> Optional[set[str]]:
    departments = _fact(row, "care_capabilities", "departments")
    levels = _fact(row, "care_capabilities", "functional_levels_served")
    found: set[str] = set()
    supplied = False
    if _facility_supplied(departments):
        supplied = True
        found |= {DEPARTMENT_LEVELS.get(str(item).strip()) for item in departments["value"]} - {None}
    if _facility_supplied(levels):
        supplied = True
        found |= {str(item).upper() for item in levels["value"]}
    return found if supplied else None


def functional_level_gate(row: Dict[str, Any], wanted: Optional[str]) -> tuple[str, str]:
    level = str(wanted or "").upper()
    if level not in FUNCTIONAL_LEVELS:
        return PENDING, "FUNCTIONAL_LEVEL_UNKNOWN_ASK_FAMILY"
    served = _levels_from(row)
    if served is None:
        return PENDING, "FACILITY_NOT_REGISTERED_OR_LEVELS_NOT_FILLED"
    if level in served:
        return PASS, "FACILITY_SUPPLIED_LEVEL"
    return FAIL, "FACILITY_DOES_NOT_SERVE_LEVEL"


def moh_code_agreement_gate(row: Dict[str, Any]) -> tuple[str, str]:
    fact = _fact(row, "licensing", "moh_code_agreement")
    if _facility_supplied(fact):
        value = str(fact["value"]).upper()
        if value == "YES":
            return PASS, "FACILITY_SUPPLIED_MOH_AGREEMENT"
        if value == "NO":
            return FAIL, "FACILITY_SUPPLIED_NO_MOH_AGREEMENT"
    return PENDING, "MOH_AGREEMENT_NOT_FILLED_BY_FACILITY"


def israel_must_haves(questionnaire_state: Dict[str, Any]) -> list[Dict[str, Any]]:
    """MUSTs from the family's structured Israeli answers (functional level, funding)."""
    answers = questionnaire_state.get("israelMarket") if isinstance(questionnaire_state.get("israelMarket"), dict) else {}
    level = str(answers.get("functionalLevel") or "").upper()
    funding = str(answers.get("fundingPathway") or "").upper()
    musts = [{
        "key": FUNCTIONAL_LEVEL_KEY,
        "value": level if level in FUNCTIONAL_LEVELS else None,
        "reason": "In Israel the resident's functional level decides which licensed setting may serve them.",
        "verification": "levels/wards the facility filled in at registration",
    }]
    if funding == "MOH_CODE":
        musts.append({
            "key": MOH_CODE_AGREEMENT_KEY,
            "value": "YES",
            "reason": "A Ministry of Health code can be used only at an institution with a Ministry agreement.",
            "verification": "MoH agreement the facility filled in at registration",
        })
    return musts
