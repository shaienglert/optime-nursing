"""Israeli MUST gates, evaluated by the shared client-intent engine.

A gate passes only on a fact the source states for this facility. A fact that
comes only from the license type's regulatory scope can exclude a facility but
never qualify it, and an unknown fact is PENDING (ask or verify), never PASS.
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


def functional_level_gate(row: Dict[str, Any], wanted: Optional[str]) -> tuple[str, str]:
    level = str(wanted or "").upper()
    if level not in FUNCTIONAL_LEVELS:
        return PENDING, "FUNCTIONAL_LEVEL_UNKNOWN_ASK_FAMILY"

    departments = _fact(row, "care_capabilities", "departments")
    if _stated(departments) and str(departments.get("basis")) == "SOURCE_LIST":
        served = {DEPARTMENT_LEVELS.get(str(item).strip()) for item in departments["value"]}
        if level in served:
            return PASS, "WARD_STATED_IN_SOURCE"

    scope = _fact(row, "care_capabilities", "functional_levels_served")
    if _stated(scope):
        levels = {str(item).upper() for item in scope["value"]}
        if level in levels and str(scope.get("basis")) == "SOURCE_LIST":
            return PASS, "LEVEL_STATED_IN_SOURCE"
        if level not in levels and not (_stated(departments) and level in {
            DEPARTMENT_LEVELS.get(str(item).strip()) for item in departments["value"]
        }):
            # Outside what this license type may serve, and no ward for it is reported.
            return FAIL, "LEVEL_OUTSIDE_LICENSE_SCOPE"
    return PENDING, "LEVEL_NOT_STATED_VERIFY_WITH_FACILITY"


def moh_code_agreement_gate(row: Dict[str, Any]) -> tuple[str, str]:
    fact = _fact(row, "licensing", "moh_code_agreement")
    if _stated(fact):
        value = str(fact["value"]).upper()
        if value == "YES":
            return PASS, "MOH_AGREEMENT_STATED"
        if value == "NO":
            return FAIL, "NO_MOH_AGREEMENT"
    return PENDING, "MOH_AGREEMENT_UNKNOWN"


def israel_must_haves(questionnaire_state: Dict[str, Any]) -> list[Dict[str, Any]]:
    """MUSTs from the family's structured Israeli answers (functional level, funding)."""
    answers = questionnaire_state.get("israelMarket") if isinstance(questionnaire_state.get("israelMarket"), dict) else {}
    level = str(answers.get("functionalLevel") or "").upper()
    funding = str(answers.get("fundingPathway") or "").upper()
    musts = [{
        "key": FUNCTIONAL_LEVEL_KEY,
        "value": level if level in FUNCTIONAL_LEVELS else None,
        "reason": "In Israel the resident's functional level decides which licensed setting may serve them.",
        "verification": "ward or level stated by the facility list or the facility; regulatory scope can only exclude",
    }]
    if funding == "MOH_CODE":
        musts.append({
            "key": MOH_CODE_AGREEMENT_KEY,
            "value": "YES",
            "reason": "A Ministry of Health code can be used only at an institution with a Ministry agreement.",
            "verification": "Ministry of Health institution list, field בהסכם",
        })
    return musts
