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
# Family funding pathway -> the facility payment track that must be ticked.
# (MOH_CODE keeps its own gate on the MoH agreement, which validation ties to the track.)
FUNDING_TRACKS = {"WELFARE_ASSISTANCE": "WELFARE", "PRIVATE": "PRIVATE"}
GENDER_KEY = "IL_GENDER_POLICY"
GENDERS = {"FEMALE", "MALE"}

ISRAEL_MUST_KEYS = (
    {FUNCTIONAL_LEVEL_KEY, MOH_CODE_AGREEMENT_KEY, COUPLE_KEY, GENDER_KEY, FUNDING_TRACK_KEY}
    | {key for key, _ in MEDICAL_NEED_GATES.values()}
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


def gender_gate(row: Dict[str, Any], genders: set[str]) -> tuple[str, str]:
    answers = _answers(row)
    if answers is None:
        return PENDING, "FACILITY_NOT_REGISTERED"
    policy = str(answers.get("gender_policy") or "").upper()
    if policy == "MIXED":
        return PASS, "FACILITY_ACCEPTS_ALL_GENDERS"
    if policy in {"WOMEN_ONLY", "MEN_ONLY"}:
        allowed = "FEMALE" if policy == "WOMEN_ONLY" else "MALE"
        return (PASS, "FACILITY_GENDER_POLICY_FITS") if genders == {allowed} else (FAIL, "FACILITY_GENDER_POLICY_EXCLUDES")
    return PENDING, "FACILITY_DID_NOT_ANSWER_GENDER_POLICY"


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
    if key == GENDER_KEY:
        return gender_gate(row, set(must.get("value") or []))
    for gate_key, question in MEDICAL_NEED_GATES.values():
        if key == gate_key:
            return yes_no_gate(row, question)
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
    if family.get("isCouple") is True:
        same = family.get("partnerSameLevel")
        musts.append({
            "key": COUPLE_KEY,
            "same_level": same if isinstance(same, bool) else None,
            "reason": "The family is looking for a place for a couple.",
            "verification": "facility answer on accepting couples",
        })
    genders = {str(g).upper() for g in family.get("residentGenders") or []} & GENDERS
    if genders:
        musts.append({
            "key": GENDER_KEY,
            "value": sorted(genders),
            "reason": "A women-only or men-only facility can serve only matching residents.",
            "verification": "facility gender policy",
        })
    return musts


# ---------------------------------------------------------------------------
# Ranking-only preferences (owner decision 2026-11-14: a mismatch ranks lower and
# never hides a facility). Outcomes: MATCH / MISMATCH / UNKNOWN.
# ---------------------------------------------------------------------------

MATCH, MISMATCH, UNKNOWN = "MATCH", "MISMATCH", "UNKNOWN"
COMMUNITIES = {"SECULAR", "TRADITIONAL", "RELIGIOUS", "HAREDI", "MUSLIM", "CHRISTIAN", "DRUZE"}
# A "mixed" Jewish facility suits families who did not ask for a religious setting.
MIXED_FITS = {"SECULAR", "TRADITIONAL"}


def israel_nice_to_haves(questionnaire_state: Dict[str, Any]) -> list[Dict[str, Any]]:
    family = _family(questionnaire_state)
    nice: list[Dict[str, Any]] = []
    community = str(family.get("community") or "").upper()
    if community in COMMUNITIES:
        nice.append({"key": "IL_COMMUNITY", "value": community, "reason": "Preferred community character."})
    kashrut = str(family.get("kashrut") or "").upper()
    if kashrut in {"KOSHER", "MEHADRIN"}:
        nice.append({"key": "IL_KASHRUT", "value": kashrut, "reason": "Kashrut matters to the family."})
    if str(family.get("shabbat") or "").upper() == "IMPORTANT":
        nice.append({"key": "IL_SHABBAT", "reason": "Shabbat observance matters to the family."})
    language = str(family.get("language") or "").upper()
    if language and language != "HE":
        nice.append({"key": "IL_LANGUAGE", "value": language, "reason": "The resident's main language."})
    if str(family.get("shelterInRoom") or "").upper() == "IMPORTANT":
        nice.append({"key": "IL_SHELTER", "reason": "A protected room close by matters to the family."})
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
    level = str(family.get("functionalLevel") or "").upper()
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
    if key == "IL_LANGUAGE":
        languages = answers.get("staff_languages")
        return UNKNOWN if not languages else (MATCH if value in languages else MISMATCH)
    if key == "IL_SHELTER":
        shelter = str(answers.get("shelter") or "").upper()
        return UNKNOWN if not shelter else (MATCH if shelter in {"ROOM", "FLOOR"} else MISMATCH)
    if key == "IL_BUDGET":
        return budget_status(row, nice)[0]
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
    "MAY_FIT": "עשוי להתאים לתקציב, בכפוף להצעה",
    "ON_REQUEST": "מחיר בבירור",
    "OVER_BUDGET": "המחיר ההתחלתי מעל התקציב",
}


def _offer_fit(offer: Dict[str, Any], budget: float, cap: Optional[float]) -> str:
    monthly, deposit = offer.get("monthly_from_ils"), offer.get("deposit_from_ils")
    if monthly is not None and monthly > budget:
        return "OVER"
    if cap is not None and deposit is not None and deposit > cap:
        return "OVER"
    if monthly is None:
        return "PARTIAL"  # deposit track without a published maintenance fee
    if offer.get("track") == "DEPOSIT" and deposit is None and cap is not None:
        return "PARTIAL"
    return "FITS"


def budget_status(row: Dict[str, Any], nice: Dict[str, Any]) -> tuple[str, str, Optional[Dict[str, Any]]]:
    """(MATCH/MISMATCH/UNKNOWN, Hebrew status label, the offer it rests on)."""
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
    for offer in at_level:
        if _offer_fit(offer, budget, cap) == "FITS":
            return MATCH, BUDGET_LABELS["IN_BUDGET"], offer
    for offer in at_level:
        if _offer_fit(offer, budget, cap) == "PARTIAL":
            return UNKNOWN, BUDGET_LABELS["MAY_FIT"], offer
    if not at_level:
        # Prices exist only for other care levels: they say little about this family's.
        cheapest = min(offers, key=lambda o: o.get("monthly_from_ils") or 10**9)
        if _offer_fit(cheapest, budget, cap) != "OVER":
            return UNKNOWN, BUDGET_LABELS["MAY_FIT"], cheapest
        return UNKNOWN, BUDGET_LABELS["ON_REQUEST"], None
    return MISMATCH, BUDGET_LABELS["OVER_BUDGET"], min(at_level, key=lambda o: o.get("monthly_from_ils") or 10**9)
