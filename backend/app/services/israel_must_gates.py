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
# Family-side only (owner 2026-11-15): served by a facility's complex-nursing ward,
# not by a level the facility ticks. Funding for it is explained, never gated.
COMPLEX_NURSING = "COMPLEX_NURSING"
FAMILY_LEVELS = FUNCTIONAL_LEVELS | {COMPLEX_NURSING}
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


def _special_units(row: Dict[str, Any]) -> Optional[set[str]]:
    """Units the facility itself listed; None when it has not registered or left the question blank."""
    if str(row.get("registration_status") or "") != "REGISTERED":
        return None
    answers = row.get("israel_questionnaire") if isinstance(row.get("israel_questionnaire"), dict) else {}
    units = answers.get("special_units")
    return {str(u).upper() for u in units} if units else None


def complex_nursing_gate(row: Dict[str, Any]) -> tuple[str, str]:
    units = _special_units(row)
    if units and COMPLEX_NURSING in units:
        return PASS, "FACILITY_HAS_COMPLEX_NURSING_WARD"
    served = _levels_from(row)
    if served is not None and "NURSING" not in served:
        return FAIL, "FACILITY_DOES_NOT_SERVE_NURSING"
    if units:
        # The facility listed its special units and complex nursing is not among them.
        return FAIL, "FACILITY_LISTED_UNITS_WITHOUT_COMPLEX_NURSING"
    return PENDING, "FACILITY_DID_NOT_STATE_COMPLEX_NURSING_WARD"


# Family need for a special unit -> MUST key. Owner 2026-11-20: a psychogeriatric
# framework stated in free text was silently dropped; it is a MUST like complex nursing.
SPECIAL_UNIT_NEEDS = {"PSYCHOGERIATRIC": "IL_PSYCHOGERIATRIC_UNIT"}


def special_unit_gate(row: Dict[str, Any], unit: str) -> tuple[str, str]:
    """PASS only when the facility listed the unit; FAIL when it listed its units without
    it; PENDING when it did not answer (missing information is not negative evidence)."""
    units = _special_units(row)
    if units and unit in units:
        return PASS, f"FACILITY_HAS_{unit}_UNIT"
    if units:
        return FAIL, f"FACILITY_LISTED_UNITS_WITHOUT_{unit}"
    return PENDING, f"FACILITY_DID_NOT_STATE_{unit}_UNIT"


def functional_level_gate(row: Dict[str, Any], wanted: Optional[str]) -> tuple[str, str]:
    level = str(wanted or "").upper()
    if level == COMPLEX_NURSING:
        return complex_nursing_gate(row)
    if level not in FUNCTIONAL_LEVELS:
        return PENDING, "FUNCTIONAL_LEVEL_UNKNOWN_ASK_FAMILY"
    served = _levels_from(row)
    if served is None:
        return PENDING, "FACILITY_NOT_REGISTERED_OR_LEVELS_NOT_FILLED"
    if level == "FRAIL" and "FRAIL" not in served and "SUPPORTIVE" in (_special_units(row) or set()):
        # Protected housing with a supportive unit ("דיור מוגן פלוס") serves frail residents.
        return PASS, "FACILITY_HAS_SUPPORTIVE_UNIT"
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
        "value": level if level in FAMILY_LEVELS else None,
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


# ---------------------------------------------------------------------------
# Owner-approved additional MUSTs (2026-11-14). Each applies only when the family
# states the need; each reads only the facility's own questionnaire answers.
# ---------------------------------------------------------------------------

MEDICAL_NEED_GATES = {
    # family need -> (MUST key, facility yes/no question)
    "VENTILATION": ("IL_ACCEPTS_VENTILATED", "accepts_ventilated"),
    "WANDERING": ("IL_WANDERING_SAFE", "wandering_safe"),
    "PEG": ("IL_ACCEPTS_PEG", "accepts_peg"),
    "NG_TUBE": ("IL_ACCEPTS_NG_TUBE", "accepts_ng_tube"),
}
COUPLE_KEY = "IL_ACCEPTS_COUPLE"
FUNDING_TRACK_KEY = "IL_FUNDING_TRACK"
SHELTER_KEY = "IL_SHELTER_MINIMUM"
BEDRIDDEN_SHELTER_KEY = "IL_BEDRIDDEN_SHELTER"
# Closer is safer: in the room/apartment, then the same floor, then elsewhere.
SHELTER_RANK = {"ROOM": 0, "FLOOR": 1, "BUILDING": 2, "NEARBY": 3}
# Family funding pathway -> the facility payment track that must be ticked.
# (MOH_CODE keeps its own gate on the MoH agreement, which validation ties to the track.)
FUNDING_TRACKS = {"WELFARE_ASSISTANCE": "WELFARE", "PRIVATE": "PRIVATE"}

ISRAEL_MUST_KEYS = (
    {FUNCTIONAL_LEVEL_KEY, MOH_CODE_AGREEMENT_KEY, COUPLE_KEY, FUNDING_TRACK_KEY, SHELTER_KEY, BEDRIDDEN_SHELTER_KEY}
    | {key for key, _ in MEDICAL_NEED_GATES.values()}
    | set(SPECIAL_UNIT_NEEDS.values())
)


def _answers(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The facility's own questionnaire, or None if it has not registered."""
    if str(row.get("registration_status") or "") != "REGISTERED":
        return None
    answers = row.get("israel_questionnaire")
    return answers if isinstance(answers, dict) else {}


def yes_no_gate(row: Dict[str, Any], question: str) -> tuple[str, str]:
    answers = _answers(row)
    if answers is None:
        return PENDING, "FACILITY_NOT_REGISTERED"
    value = str(answers.get(question) or "").upper()
    if value == "YES":
        return PASS, f"FACILITY_SUPPLIED_{question.upper()}_YES"
    if value == "NO":
        return FAIL, f"FACILITY_SUPPLIED_{question.upper()}_NO"
    return PENDING, f"FACILITY_DID_NOT_ANSWER_{question.upper()}"


def funding_track_gate(row: Dict[str, Any], track: str) -> tuple[str, str]:
    """payment_tracks is a required question, so a registered facility always answered
    it: a track it did not tick is a stated "no"."""
    answers = _answers(row)
    if answers is None:
        return PENDING, "FACILITY_NOT_REGISTERED"
    tracks = answers.get("payment_tracks")
    if not tracks:
        return PENDING, "FACILITY_DID_NOT_ANSWER_PAYMENT_TRACKS"
    return (PASS, f"FACILITY_ACCEPTS_{track}") if track in tracks else (FAIL, f"FACILITY_DOES_NOT_ACCEPT_{track}")


def _shelter_need(family: Dict[str, Any]) -> Optional[str]:
    need = str(family.get("shelterNeed") or "").upper()
    if need in {"ROOM", "FLOOR"}:
        return need
    # Older sessions: "shelter in room or on the floor matters".
    if str(family.get("shelterInRoom") or "").upper() == "IMPORTANT":
        return "FLOOR"
    return None


def shelter_meets(answers: Optional[Dict[str, Any]], minimum: str) -> str:
    """PASS if the facility's protected space is at least as close as the family's
    minimum; PENDING if the facility has not said."""
    if answers is None:
        return PENDING
    shelter = str(answers.get("shelter") or "").upper()
    if shelter not in SHELTER_RANK:
        return PENDING
    return PASS if SHELTER_RANK[shelter] <= SHELTER_RANK[minimum] else FAIL


def couple_gate(row: Dict[str, Any], same_level: Optional[bool]) -> tuple[str, str]:
    answers = _answers(row)
    if answers is None:
        return PENDING, "FACILITY_NOT_REGISTERED"
    policy = str(answers.get("couples") or "").upper()
    if policy == "MIXED_LEVELS":
        return PASS, "FACILITY_ACCEPTS_COUPLES_ANY_LEVEL"
    if policy == "NO":
        return FAIL, "FACILITY_DOES_NOT_ACCEPT_COUPLES"
    if policy == "SAME_LEVEL":
        if same_level is True:
            return PASS, "FACILITY_ACCEPTS_COUPLES_SAME_LEVEL"
        if same_level is False:
            return FAIL, "FACILITY_ACCEPTS_ONLY_SAME_LEVEL_COUPLES"
        return PENDING, "ASK_FAMILY_WHETHER_PARTNERS_SHARE_LEVEL"
    return PENDING, "FACILITY_DID_NOT_ANSWER_COUPLES"


FAMILY_REQUIREMENTS = {
    "minBedrooms": ("IL_BEDROOMS", "max_bedrooms"),
    "privateCaregiver": ("IL_PRIVATE_CAREGIVER", None),
    "parkingType": ("IL_PARKING", "parking_types"),
    "petRequired": ("IL_PET", "pets"),
    "requiredDiets": ("IL_DIETS", "diets"),
}


def evaluate_israel_must(row: Dict[str, Any], must: Dict[str, Any]) -> tuple[str, str]:
    key = str(must.get("key") or "")
    if key == FUNCTIONAL_LEVEL_KEY:
        return functional_level_gate(row, must.get("value"))
    if key == MOH_CODE_AGREEMENT_KEY:
        return moh_code_agreement_gate(row)
    if key == COUPLE_KEY:
        return couple_gate(row, must.get("same_level"))
    if key == FUNDING_TRACK_KEY:
        return funding_track_gate(row, str(must.get("value") or ""))
    if key == BEDRIDDEN_SHELTER_KEY:
        answers = _answers(row)
        if answers is None:
            return PENDING, "FACILITY_NOT_REGISTERED"
        plan = str(answers.get("shelter_bedridden") or "").upper()
        if plan in {"PROTECTED_IN_ROOM", "MOVED_IN_BED"}:
            return PASS, "FACILITY_PROTECTS_BEDRIDDEN_RESIDENTS"
        if plan == "NO_SOLUTION":
            return FAIL, "FACILITY_HAS_NO_PROTECTION_FOR_BEDRIDDEN"
        # "No bedridden residents here" says nothing about whether it could protect one.
        return PENDING, "FACILITY_DID_NOT_STATE_BEDRIDDEN_PROTECTION"
    if key == "IL_NURSING_CONTINUITY":
        return yes_no_gate(row, "on_site_nursing_continuity")
    if key == SHELTER_KEY:
        outcome = shelter_meets(_answers(row), str(must.get("value") or "FLOOR"))
        return outcome, {PASS: "FACILITY_SHELTER_MEETS_MINIMUM", FAIL: "FACILITY_SHELTER_FARTHER_THAN_MINIMUM"}.get(outcome, "FACILITY_DID_NOT_ANSWER_SHELTER")
    for gate_key, question in MEDICAL_NEED_GATES.values():
        if key == gate_key:
            return yes_no_gate(row, question)
    for unit, gate_key in SPECIAL_UNIT_NEEDS.items():
        if key == gate_key:
            return special_unit_gate(row, unit)
    for gate_key, field in FAMILY_REQUIREMENTS.values():
        if key != gate_key:
            continue
        value = must["value"]
        if key == "IL_PRIVATE_CAREGIVER":
            if value == "UNCLEAR":
                return PENDING, "FAMILY_CAREGIVER_ARRANGEMENT_UNCLEAR"
            policy_field = "private_caregiver_live_in" if value == "LIVE_IN" else "private_caregiver_visits"
            policy = (_answers(row) or {}).get(policy_field)
            if policy == "AT_ADMISSION":
                return PASS, "FACILITY_ALLOWS_PRIVATE_CAREGIVER_AT_ADMISSION"
            if policy in ("ONLY_AFTER_ADMISSION", "NO"):
                return FAIL, "FACILITY_DOES_NOT_ALLOW_PRIVATE_CAREGIVER_AT_ADMISSION"
            return PENDING, "FACILITY_DID_NOT_CONFIRM_PRIVATE_CAREGIVER_AT_ADMISSION"
        if key == "IL_PET":
            return yes_no_gate(row, field)
        answer = (_answers(row) or {}).get(field)
        if key == "IL_BEDROOMS" and isinstance(answer, (int, float)):
            return (PASS if answer >= value else FAIL), "FACILITY_STATED_BEDROOM_COUNT"
        if isinstance(answer, list) and answer:
            required = {value} if key == "IL_PARKING" else set(value)
            offered = set(answer)
            if "NONE" in offered:
                offered = set()
            if key == "IL_PARKING" and value == "REGULAR":
                return (PASS if offered else FAIL), "FACILITY_STATED_PARKING"
            return (PASS if required <= offered else FAIL), "FACILITY_STATED_OPTIONS"
        return PENDING, "FACILITY_DID_NOT_ANSWER"
    return PENDING, "UNKNOWN_ISRAEL_MUST"


def _family(questionnaire_state: Dict[str, Any]) -> Dict[str, Any]:
    answers = questionnaire_state.get("israelMarket")
    return answers if isinstance(answers, dict) else {}


def israel_additional_musts(questionnaire_state: Dict[str, Any]) -> list[Dict[str, Any]]:
    family = _family(questionnaire_state)
    musts: list[Dict[str, Any]] = []
    track = FUNDING_TRACKS.get(str(family.get("fundingPathway") or "").upper())
    if track:
        # Owner decision 3 (funding pathway is a MUST), extended from the MoH code to the
        # welfare and private pathways once facilities report their payment tracks.
        musts.append({
            "key": FUNDING_TRACK_KEY,
            "value": track,
            "reason": "The facility must accept the family's way of paying.",
            "verification": "payment tracks the facility ticked",
        })
    needs = {str(n).upper() for n in family.get("medicalNeeds") or []}
    for need, (key, question) in MEDICAL_NEED_GATES.items():
        if need in needs:
            musts.append({
                "key": key,
                "reason": f"The family stated a {need.lower()} need.",
                "verification": f"facility answer to '{question}'",
            })
    units = {str(u).upper() for u in family.get("specialUnits") or []}
    for unit, key in SPECIAL_UNIT_NEEDS.items():
        if unit in units:
            musts.append({
                "key": key,
                "reason": f"The family needs a {unit.lower()} unit.",
                "verification": "special units the facility listed",
            })
    if family.get("isCouple") is True:
        same = family.get("partnerSameLevel")
        musts.append({
            "key": COUPLE_KEY,
            "same_level": same if isinstance(same, bool) else None,
            "reason": "The family is looking for a place for a couple.",
            "verification": "facility answer on accepting couples",
        })
    if family.get("bedridden") is True:
        # Owner, 2026-11-15: a bedridden resident is shown only where the facility has a
        # protected solution for residents in bed.
        musts.append({
            "key": BEDRIDDEN_SHELTER_KEY,
            "reason": "The resident is bedridden and must be protected during an alert.",
            "verification": "facility answer on protecting bedridden residents",
        })
    need = _shelter_need(family)
    if need and family.get("shelterIsCondition") is True:
        musts.append({
            "key": SHELTER_KEY,
            "value": need,
            "reason": "The family made a protected space this close a condition.",
            "verification": "where the facility says its protected space is",
        })
    if family.get("functionalLevel") == "INDEPENDENT" and family.get("nursingContinuity") == "REQUIRED":
        musts.append({"key": "IL_NURSING_CONTINUITY", "reason": "Family requires an on-site nursing transition option."})
    requirements = {
        "minBedrooms": lambda v: type(v) is int and 1 <= v <= 20,
        "privateCaregiver": lambda v: v in ("VISITS", "LIVE_IN", "UNCLEAR"),
        "parkingType": lambda v: v in ("REGULAR", "ACCESSIBLE", "COVERED"),
        "petRequired": lambda v: v is True,
        "requiredDiets": lambda v: isinstance(v, list) and bool(v) and all(
            d in ("DIABETIC", "TEXTURE_MODIFIED", "VEGETARIAN", "GLUTEN_FREE", "LOW_SALT", "VEGAN", "HALAL") for d in v
        ),
    }
    for field, (key, _) in FAMILY_REQUIREMENTS.items():
        value = family.get(field)
        if requirements[field](value):
            musts.append({"key": key, "value": value, "reason": "Explicit family requirement."})
    return musts


# ---------------------------------------------------------------------------
# Ranking-only preferences (owner decision 2026-11-14: a mismatch ranks lower and
# never hides a facility). Outcomes: MATCH / MISMATCH / UNKNOWN.
# ---------------------------------------------------------------------------

MATCH, MISMATCH, UNKNOWN = "MATCH", "MISMATCH", "UNKNOWN"
ACTIVITY_CODES = {"GARDENING", "CRAFTS", "GAMES", "MUSIC", "LECTURES", "MOVEMENT", "OUTINGS", "SPIRITUAL"}
COMMUNITIES = {"SECULAR", "TRADITIONAL", "RELIGIOUS", "HAREDI", "MUSLIM", "CHRISTIAN", "DRUZE"}
# A "mixed" Jewish facility suits families who did not ask for a religious setting.
MIXED_FITS = {"SECULAR", "TRADITIONAL"}


def israel_nice_to_haves(questionnaire_state: Dict[str, Any]) -> list[Dict[str, Any]]:
    family = _family(questionnaire_state)
    nice: list[Dict[str, Any]] = []
    if family.get("functionalLevel") == "INDEPENDENT" and family.get("nursingContinuity") == "PREFERRED":
        nice.append({"key": "IL_NURSING_CONTINUITY", "reason": "Family prefers an on-site nursing transition option."})
    community = str(family.get("community") or "").upper()
    if community in COMMUNITIES:
        nice.append({"key": "IL_COMMUNITY", "value": community, "reason": "Preferred community character."})
    kashrut = str(family.get("kashrut") or "").upper()
    if kashrut in {"KOSHER", "MEHADRIN"}:
        nice.append({"key": "IL_KASHRUT", "value": kashrut, "reason": "Kashrut matters to the family."})
    if str(family.get("shabbat") or "").upper() == "IMPORTANT":
        nice.append({"key": "IL_SHABBAT", "reason": "Shabbat observance matters to the family."})
    if str(family.get("sameGenderCare") or "").upper() == "IMPORTANT":
        nice.append({"key": "IL_SAME_GENDER_CARE", "reason": "Personal care by a caregiver of the same gender."})
    language = str(family.get("language") or "").upper()
    if language and language != "HE":
        nice.append({"key": "IL_LANGUAGE", "value": language, "reason": "The resident's main language."})
    need = _shelter_need(family)
    if need and not family.get("shelterIsCondition"):
        nice.append({"key": "IL_SHELTER", "value": need, "reason": "Protected space close by matters to the family."})
    budget = family.get("monthlyBudgetIls")
    if str(family.get("fundingPathway") or "").upper() == "PRIVATE" and isinstance(budget, (int, float)) and budget > 0:
        cap = family.get("depositCapIls")
        nice.append({
            "key": "IL_BUDGET",
            "value": float(budget),
            "deposit_cap": float(cap) if isinstance(cap, (int, float)) and cap >= 0 else None,
            "level": str(family.get("functionalLevel") or "").upper() or None,
            "reason": "Monthly budget (and deposit ceiling) for private payment.",
        })
    from app.services.israel_geo import locate

    origin = locate(family.get("city"))
    if origin:
        # Closer ranks higher among otherwise equal facilities (never a match/mismatch).
        nice.append({"key": "IL_PROXIMITY", "value": {"lat": origin[0], "lon": origin[1]}, "reason": "Distance from the family's locality."})
        max_km = family.get("maxDistanceKm")
        if isinstance(max_km, (int, float)) and max_km > 0:
            nice.append({
                "key": "IL_DISTANCE",
                "value": {"lat": origin[0], "lon": origin[1], "max_km": float(max_km)},
                "reason": "Within the distance the family chose (ranking only).",
            })
    # Lifestyle (owner, 2026-11-15: "שאלות על אופי החיים"): ranking only, like community.
    priority = str(family.get("priority") or "").upper()
    if priority in {"MEDICAL", "SOCIAL", "SAFETY"}:
        nice.append({"key": "IL_PRIORITY", "value": priority, "reason": "What matters most today."})
    setting = str(family.get("setting") or "").upper()
    if setting in {"URBAN", "RURAL"}:
        nice.append({"key": "IL_SETTING", "value": setting, "reason": "Preferred surroundings."})
    styles = sorted({str(v).upper() for v in family.get("styles") or []} & {"LUXURY", "MODERN", "BOUTIQUE", "HOMEY"})
    if styles:
        nice.append({"key": "IL_STYLE", "value": styles, "reason": "Preferred style of the place."})
    rhythm = str(family.get("dayRhythm") or "").upper()
    if rhythm in {"PRIVATE_SPACE", "PEOPLE_AROUND", "STRUCTURED", "FLEXIBLE"}:
        nice.append({"key": "IL_DAY_RHYTHM", "value": rhythm, "reason": "Preferred daily rhythm."})
    activities = sorted({str(v).upper() for v in family.get("activities") or []} & ACTIVITY_CODES)
    if activities:
        nice.append({"key": "IL_ACTIVITIES", "value": activities, "reason": "Activities the resident would enjoy."})
    level = str(family.get("functionalLevel") or "").upper()
    level = "NURSING" if level == COMPLEX_NURSING else level
    if level in FUNCTIONAL_LEVELS:
        nice.append({"key": "IL_AVAILABILITY", "value": level, "reason": "A place available soon at the needed level."})
    return nice


def distance_km(row: Dict[str, Any], origin: Dict[str, Any]) -> Optional[float]:
    from app.services.israel_geo import facility_point, km_between

    point, _ = facility_point(row)
    if point is None:
        return None
    return round(km_between((float(origin["lat"]), float(origin["lon"])), point), 1)


def evaluate_israel_nice(row: Dict[str, Any], nice: Dict[str, Any]) -> str:
    if str(nice.get("key")) == "IL_DISTANCE":
        # Location comes from the list or locality, not the questionnaire, so it applies
        # to unregistered facilities too.
        km = distance_km(row, nice["value"])
        if km is None:
            return UNKNOWN
        return MATCH if km <= float(nice["value"]["max_km"]) else MISMATCH
    answers = _answers(row)
    if answers is None:
        return UNKNOWN
    key = str(nice.get("key") or "")
    value = nice.get("value")
    if key == "IL_NURSING_CONTINUITY":
        outcome, _ = yes_no_gate(row, "on_site_nursing_continuity")
        return {PASS: MATCH, FAIL: MISMATCH}.get(outcome, UNKNOWN)
    if key == "IL_COMMUNITY":
        character = str(answers.get("religious_character") or "").upper()
        if not character:
            return UNKNOWN
        if character == value or (character == "MIXED" and value in MIXED_FITS):
            return MATCH
        return MISMATCH
    if key == "IL_KASHRUT":
        kashrut = str(answers.get("kashrut") or "").upper()
        if not kashrut:
            return UNKNOWN
        ok = {"KOSHER": {"KOSHER", "MEHADRIN"}, "MEHADRIN": {"MEHADRIN"}}[value]
        return MATCH if kashrut in ok else MISMATCH
    if key == "IL_SHABBAT":
        shabbat = str(answers.get("shabbat") or "").upper()
        return UNKNOWN if not shabbat else (MATCH if shabbat == "OBSERVED" else MISMATCH)
    if key == "IL_SAME_GENDER_CARE":
        same = str(answers.get("same_gender_care") or "").upper()
        return UNKNOWN if not same else (MATCH if same == "YES" else MISMATCH)
    if key == "IL_LANGUAGE":
        languages = answers.get("staff_languages")
        return UNKNOWN if not languages else (MATCH if value in languages else MISMATCH)
    if key == "IL_SHELTER":
        outcome = shelter_meets(answers, str(value or "FLOOR"))
        return {PASS: MATCH, FAIL: MISMATCH}.get(outcome, UNKNOWN)
    if key == "IL_BUDGET":
        return budget_status(row, nice)[0]
    if key == "IL_PRIORITY":
        if value == "MEDICAL":
            nurse = str(answers.get("nurse_24_7") or "").upper()
            return UNKNOWN if not nurse else (MATCH if nurse == "YES" else MISMATCH)
        if value == "SOCIAL":
            atmosphere = str(answers.get("social_atmosphere") or "").upper()
            return UNKNOWN if not atmosphere else (MATCH if atmosphere in {"LIVELY", "BOTH"} else MISMATCH)
        if value == "SAFETY":
            shelter = str(answers.get("shelter") or "").upper()
            return UNKNOWN if not shelter else (MATCH if shelter in {"ROOM", "FLOOR"} else MISMATCH)
        return UNKNOWN
    if key == "IL_SETTING":
        setting = str(answers.get("setting") or "").upper()
        if not setting or setting == "SUBURBAN":
            return UNKNOWN  # in between: neither a match nor a mismatch
        return MATCH if setting == value else MISMATCH
    if key == "IL_STYLE":
        style = str(answers.get("style") or "").upper()
        return UNKNOWN if not style else (MATCH if style in value else MISMATCH)
    if key == "IL_DAY_RHYTHM":
        if value in {"STRUCTURED", "FLEXIBLE"}:
            day = str(answers.get("day_style") or "").upper()
            return UNKNOWN if not day else (MATCH if day in {value, "BOTH"} else MISMATCH)
        if value == "PEOPLE_AROUND":
            atmosphere = str(answers.get("social_atmosphere") or "").upper()
            return UNKNOWN if not atmosphere else (MATCH if atmosphere in {"LIVELY", "BOTH"} else MISMATCH)
        rooms = answers.get("room_types")  # PRIVATE_SPACE: a room of one's own
        if not rooms:
            return UNKNOWN
        return MATCH if set(rooms) & {"SINGLE", "COUPLE_UNIT", "APARTMENT", "STUDIO", "APT_2", "APT_3"} else MISMATCH
    if key == "IL_ACTIVITIES":
        offered = answers.get("activities_offered")
        return UNKNOWN if not offered else (MATCH if set(offered) & set(value) else MISMATCH)
    if key == "IL_AVAILABILITY":
        vacancy = str((answers.get("vacancy_by_level") or {}).get(value) or "").upper()
        if not vacancy:
            return UNKNOWN
        return MATCH if vacancy in {"AVAILABLE_NOW", "WITHIN_MONTH"} else MISMATCH
    return UNKNOWN


# ---------------------------------------------------------------------------
# Budget against published starting prices (owner spec, 2026-11-15).
# A starting price is a floor for one track / room type / care level. The family
# sees one of four statuses; only "over budget" lowers the ranking.
# ---------------------------------------------------------------------------

BUDGET_LABELS = {
    "IN_BUDGET": "בתקציב לפי המחיר ההתחלתי",
    "NEAR": "מעל התקציב ב-{pct}% (בתוך סטייה של עד 10%)",
    "MAY_FIT": "עשוי להתאים לתקציב, בכפוף להצעה",
    "ON_REQUEST": "מחיר בבירור",
    "OVER_BUDGET": "המחיר ההתחלתי מעל התקציב",
}
# Owner, 2026-11-15: allow up to 10% above the family's ceilings, and say so.
BUDGET_TOLERANCE = 0.10


def _over_ratio(offer: Dict[str, Any], budget: float, cap: Optional[float]) -> float:
    """How far the offer's known amounts exceed the family's ceilings (0 = within)."""
    ratios = [0.0]
    monthly, deposit = offer.get("monthly_from_ils"), offer.get("deposit_from_ils")
    if monthly is not None and budget > 0:
        ratios.append(monthly / budget - 1)
    if cap is not None and deposit is not None:
        ratios.append(float("inf") if cap == 0 and deposit > 0 else (deposit / cap - 1 if cap > 0 else 0.0))
    return max(ratios)


def _offer_fit(offer: Dict[str, Any], budget: float, cap: Optional[float]) -> str:
    ratio = _over_ratio(offer, budget, cap)
    if ratio > BUDGET_TOLERANCE + 1e-9:
        return "OVER"
    if offer.get("monthly_from_ils") is None:
        return "PARTIAL"  # deposit track without a published maintenance fee
    if offer.get("track") == "DEPOSIT" and offer.get("deposit_from_ils") is None and cap is not None:
        return "PARTIAL"
    return "FITS" if ratio <= 1e-9 else "NEAR"


def budget_status(row: Dict[str, Any], nice: Dict[str, Any]) -> tuple[str, str, Optional[Dict[str, Any]]]:
    """(MATCH/MISMATCH/UNKNOWN, Hebrew status label, the offer it rests on).

    Within budget ranks higher; up to 10% above is neutral and labelled as above
    budget; more than 10% above ranks lower. Nothing here hides a facility.
    """
    answers = _answers(row)
    offers = (answers or {}).get("price_offers") or []
    legacy = _fact(row, "pricing", "monthly_price")
    if not offers and _facility_supplied(legacy):
        # Registrations saved before price offers existed: one undifferentiated price.
        offers = [{"track": "MONTHLY", "level": None, "room_type": None, "monthly_from_ils": int(legacy["value"]), "deposit_from_ils": None}]
    if answers is None or not offers or (answers or {}).get("price_publication") == "WITHHOLD":
        return UNKNOWN, BUDGET_LABELS["ON_REQUEST"], None

    budget, cap, level = float(nice["value"]), nice.get("deposit_cap"), nice.get("level")
    at_level = [o for o in offers if o.get("level") in (None, level)]
    fits = {id(o): _offer_fit(o, budget, cap) for o in offers}
    for offer in at_level:
        if fits[id(offer)] == "FITS":
            return MATCH, BUDGET_LABELS["IN_BUDGET"], offer
    near = [o for o in at_level if fits[id(o)] == "NEAR"]
    if near:
        best = min(near, key=lambda o: _over_ratio(o, budget, cap))
        pct = max(1, round(_over_ratio(best, budget, cap) * 100))
        return UNKNOWN, BUDGET_LABELS["NEAR"].format(pct=pct), best
    for offer in at_level:
        if fits[id(offer)] == "PARTIAL":
            return UNKNOWN, BUDGET_LABELS["MAY_FIT"], offer
    if not at_level:
        # Prices exist only for other care levels: they say little about this family's.
        cheapest = min(offers, key=lambda o: o.get("monthly_from_ils") or 10**9)
        if fits[id(cheapest)] != "OVER":
            return UNKNOWN, BUDGET_LABELS["MAY_FIT"], cheapest
        return UNKNOWN, BUDGET_LABELS["ON_REQUEST"], None
    return MISMATCH, BUDGET_LABELS["OVER_BUDGET"], min(at_level, key=lambda o: o.get("monthly_from_ils") or 10**9)
