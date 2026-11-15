"""Generate 450 synthetic Israeli facilities for test runs of the matching engine.

Every record is fake and marked as such (IDs IL-SYN-###, names prefixed
"[סינתטי]", flag SYNTHETIC_TEST_DATA, no real phone numbers or websites). They load
only in the `israel-synthetic` market, never alongside real facilities.

What is grounded and what is assumed:
- Setting mix and city weights follow the real Israeli universe in this repo
  (255 MoH / 115 welfare / 97 protected-housing rows; cities weighted by count).
- Price ranges follow published directory ranges (d.co.il price list, 2025):
  protected housing full deposit ₪0.5-1.5M with ~3%/year depreciation and
  ₪3.5-7.5k monthly, no-deposit ₪10-18k; nursing ₪7-18.5k by region.
- Everything else (community mix, language mix, capability rates, availability,
  shares of unregistered / partially answered facilities) is an assumption chosen
  to cover the decision space, NOT a measurement of the Israeli market.
- City coordinates are approximate city centres (±0.02° jitter added).

Deterministic: the same seed always produces the same 450 facilities.

Usage: python scripts/generate_israel_synthetic_facilities.py [--seed 20261115]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.israel_facility_registration import validate_registration  # noqa: E402

OUT_DIR = ROOT / "database" / "israel_synthetic"
TOTAL = 450
SCHEMA = "israel-canonical-facility-v1.0.0"
GENERATED_AT = "2026-11-15T06:00:00Z"

# city -> (lat, lon, region, community weights override)
JEWISH = {"SECULAR": 35, "TRADITIONAL": 25, "RELIGIOUS": 12, "HAREDI": 6, "MIXED": 22}
CITIES = {
    "ירושלים": (31.78, 35.22, "CENTER", {"SECULAR": 15, "TRADITIONAL": 25, "RELIGIOUS": 25, "HAREDI": 25, "MIXED": 10}),
    "חיפה": (32.80, 34.99, "NORTH", {"SECULAR": 45, "TRADITIONAL": 20, "RELIGIOUS": 8, "HAREDI": 4, "MIXED": 23}),
    "תל אביב - יפו": (32.08, 34.78, "CENTER", {"SECULAR": 55, "TRADITIONAL": 18, "RELIGIOUS": 5, "HAREDI": 2, "MIXED": 20}),
    "ראשון לציון": (31.97, 34.80, "CENTER", JEWISH),
    "באר שבע": (31.25, 34.79, "SOUTH", JEWISH),
    "בני ברק": (32.08, 34.83, "CENTER", {"RELIGIOUS": 10, "HAREDI": 85, "MIXED": 5}),
    "נתניה": (32.32, 34.86, "CENTER", JEWISH),
    "הרצליה": (32.16, 34.84, "CENTER", JEWISH),
    "פתח תקווה": (32.09, 34.89, "CENTER", JEWISH),
    "רמת גן": (32.07, 34.82, "CENTER", JEWISH),
    "כפר סבא": (32.18, 34.91, "CENTER", JEWISH),
    "נהריה": (33.01, 35.10, "NORTH", JEWISH),
    "חדרה": (32.43, 34.92, "NORTH", JEWISH),
    "רחובות": (31.89, 34.81, "CENTER", JEWISH),
    "קרית טבעון": (32.72, 35.13, "NORTH", JEWISH),
    "טבריה": (32.79, 35.53, "NORTH", JEWISH),
    "רעננה": (32.18, 34.87, "CENTER", JEWISH),
    "גדרה": (31.81, 34.78, "CENTER", JEWISH),
    "בת ים": (32.02, 34.75, "CENTER", JEWISH),
    "אשקלון": (31.67, 34.57, "SOUTH", JEWISH),
    "גבעתיים": (32.07, 34.81, "CENTER", JEWISH),
    "עפולה": (32.61, 35.29, "NORTH", JEWISH),
    "חולון": (32.01, 34.78, "CENTER", JEWISH),
    "אשדוד": (31.80, 34.65, "SOUTH", JEWISH),
    "הוד השרון": (32.15, 34.89, "CENTER", JEWISH),
    "רמת השרון": (32.15, 34.84, "CENTER", JEWISH),
    "קרית ים": (32.85, 35.07, "NORTH", JEWISH),
    "אופקים": (31.31, 34.62, "SOUTH", JEWISH),
    "קרית אתא": (32.81, 35.11, "NORTH", JEWISH),
    "עכו": (32.93, 35.08, "NORTH", {"SECULAR": 30, "TRADITIONAL": 25, "MIXED": 20, "MUSLIM": 25}),
    "נוף הגליל": (32.70, 35.32, "NORTH", JEWISH),
    "דימונה": (31.07, 35.03, "SOUTH", JEWISH),
    "קרית ביאליק": (32.84, 35.09, "NORTH", JEWISH),
    "מודיעין": (31.90, 35.01, "CENTER", JEWISH),
    "אילת": (29.56, 34.95, "SOUTH", JEWISH),
    "צפת": (32.96, 35.50, "NORTH", {"TRADITIONAL": 25, "RELIGIOUS": 30, "HAREDI": 35, "MIXED": 10}),
    "בית שמש": (31.75, 34.99, "CENTER", {"TRADITIONAL": 20, "RELIGIOUS": 30, "HAREDI": 45, "MIXED": 5}),
    "נצרת": (32.70, 35.30, "NORTH", {"MUSLIM": 55, "CHRISTIAN": 45}),
    "כפר יאסיף": (32.95, 35.16, "NORTH", {"CHRISTIAN": 60, "MUSLIM": 25, "DRUZE": 15}),
    "שפרעם": (32.81, 35.17, "NORTH", {"MUSLIM": 55, "CHRISTIAN": 20, "DRUZE": 25}),
    "אום אל-פחם": (32.52, 35.15, "NORTH", {"MUSLIM": 100}),
    "טייבה": (32.27, 35.01, "CENTER", {"MUSLIM": 100}),
    "רהט": (31.39, 34.75, "SOUTH", {"MUSLIM": 100}),
    "דלית אל-כרמל": (32.69, 35.05, "NORTH", {"DRUZE": 100}),
    "ירכא": (32.95, 35.21, "NORTH", {"DRUZE": 100}),
}
# Weights from the real universe's city counts (Arab-sector towns get a small floor
# so the engine is exercised on them; the real lists include very few).
CITY_WEIGHTS = {
    "ירושלים": 51, "חיפה": 43, "תל אביב - יפו": 25, "ראשון לציון": 18, "באר שבע": 17, "בני ברק": 16,
    "נתניה": 14, "הרצליה": 13, "פתח תקווה": 20, "רמת גן": 13, "כפר סבא": 11, "נהריה": 10, "חדרה": 8,
    "רחובות": 8, "קרית טבעון": 7, "טבריה": 6, "רעננה": 6, "גדרה": 5, "בת ים": 5, "אשקלון": 5,
    "גבעתיים": 5, "עפולה": 4, "חולון": 4, "אשדוד": 4, "הוד השרון": 4, "רמת השרון": 4, "קרית ים": 4,
    "אופקים": 3, "קרית אתא": 3, "עכו": 3, "נוף הגליל": 2, "דימונה": 2, "קרית ביאליק": 2,
    "מודיעין": 3, "אילת": 2, "צפת": 3, "בית שמש": 4,
    "נצרת": 8, "שפרעם": 4, "כפר יאסיף": 3, "אום אל-פחם": 4, "טייבה": 3, "רהט": 3, "דלית אל-כרמל": 3, "ירכא": 2,
}
NAME_WORDS = ["נוף", "אלון", "הדר", "שלווה", "גני", "בית", "נווה", "אחוזת", "מעונות", "פסגת", "גבעת", "עדן", "רמת", "יד", "אור"]
NAME_TAILS = ["הזהב", "השקמה", "הכרמל", "השרון", "התמר", "הגליל", "הים", "הגפן", "הדקל", "האורנים", "השלום", "הנחל"]

# Setting -> share, levels and other generation rules.
SETTINGS = [
    ("IL_NURSING_HOME", 245, "בית אבות סיעודי", "MOH"),
    ("IL_WELFARE_HOME", 111, "בית אבות", "WEL"),
    ("IL_PROTECTED_HOUSING", 94, "דיור מוגן", "DM"),
]
REGION_PRICE = {"CENTER": 1.0, "NORTH": 0.88, "SOUTH": 0.8}


def chance(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def pick(rng: random.Random, weights: dict) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def subset(rng: random.Random, probabilities: dict) -> list:
    return sorted(k for k, p in probabilities.items() if chance(rng, p))


def round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


def build_offers(rng, setting, levels, monthly, deposit, vacancy):
    """Published starting prices, including the three cases the owner asked to test:
    no price, a starting price whose room/level has no place, and the same monthly
    payment in two tracks with different deposits."""
    if chance(rng, 0.1):
        return "NO_PRICE", "WITHHOLD", []
    offers = []
    if setting == "IL_PROTECTED_HOUSING":
        level = "INDEPENDENT"
        if deposit:
            apartment = rng.choice(["STUDIO", "APT_2"])
            offers.append({"track": "DEPOSIT", "room_type": apartment, "level": level, "monthly_from_ils": monthly, "deposit_from_ils": deposit})
            if chance(rng, 0.3):
                # Same maintenance fee, bigger apartment, larger deposit.
                offers.append({"track": "DEPOSIT", "room_type": "APT_3", "level": level, "monthly_from_ils": monthly, "deposit_from_ils": round_to(deposit * rng.uniform(1.3, 1.8), 10_000)})
                case = "SAME_MONTHLY_TWO_DEPOSITS"
            elif chance(rng, 0.12):
                offers[0]["monthly_from_ils"] = None  # deposit published, maintenance on request
                case = "DEPOSIT_ONLY"
            else:
                case = "PUBLISHED"
        else:
            offers.append({"track": "MONTHLY", "room_type": rng.choice(["STUDIO", "APT_2"]), "level": level, "monthly_from_ils": monthly, "deposit_from_ils": None})
            case = "PUBLISHED"
        if "NURSING" in levels and chance(rng, 0.6):
            offers.append({"track": "MONTHLY", "room_type": "SHARED_2", "level": "NURSING", "monthly_from_ils": round_to(monthly * 1.4 + 9000, 250), "deposit_from_ils": None})
        return case, "PUBLISH", offers

    priced_levels = [lv for lv in ("FRAIL", "NURSING", "COGNITIVE_FRAIL", "INDEPENDENT") if lv in levels]
    for index, level in enumerate(priced_levels[: rng.choice([1, 2, 2, 3])]):
        bump = {"INDEPENDENT": 0.85, "FRAIL": 0.9, "NURSING": 1.0, "COGNITIVE_FRAIL": 1.1}[level]
        shared = round_to(monthly * bump, 250)
        offers.append({"track": "MONTHLY", "room_type": "SHARED_2", "level": level, "monthly_from_ils": shared, "deposit_from_ils": None})
        if chance(rng, 0.35):
            offers.append({"track": "MONTHLY", "room_type": "SINGLE", "level": level, "monthly_from_ils": round_to(shared * rng.uniform(1.2, 1.35), 250), "deposit_from_ils": None})
    cheapest = min(offers, key=lambda o: o["monthly_from_ils"])
    if vacancy.get(cheapest["level"]) in {"WAITLIST", "NONE"}:
        return "CHEAPEST_HAS_NO_PLACE", "PUBLISH", offers
    return "PUBLISHED", "PUBLISH", offers


def build_answers(rng: random.Random, setting: str, community: str, region: str, number: int, city: str):
    arab = community in {"MUSLIM", "CHRISTIAN", "DRUZE"}
    price_factor = REGION_PRICE[region] * rng.uniform(0.85, 1.2)

    if setting == "IL_NURSING_HOME":
        levels = ["NURSING"] + subset(rng, {"COGNITIVE_FRAIL": 0.6, "FRAIL": 0.4, "INDEPENDENT": 0.08})
        authority = "MINISTRY_OF_HEALTH"
        moh = chance(rng, 0.7)
        monthly = round_to(14500 * price_factor, 250)
        monthly_max = monthly + round_to(rng.uniform(1500, 6000), 250)
        deposit = None
        couples = pick(rng, {"NO": 55, "SAME_LEVEL": 30, "MIXED_LEVELS": 15})
        units = subset(rng, {"COMPLEX_NURSING": 0.25, "PSYCHOGERIATRIC": 0.08, "GERIATRIC_REHAB": 0.15, "HOSPICE": 0.15})
        ventilated = "YES" if chance(rng, 0.12) else "NO"
        wandering = ("YES" if chance(rng, 0.75) else "NO") if "COGNITIVE_FRAIL" in levels else ("YES" if chance(rng, 0.15) else "NO")
        peg = "YES" if chance(rng, 0.7) else "NO"
        ng = "YES" if chance(rng, 0.55) else "NO"
        nurse = "YES"
    elif setting == "IL_WELFARE_HOME":
        levels = subset(rng, {"INDEPENDENT": 0.7, "FRAIL": 0.92, "COGNITIVE_FRAIL": 0.2, "NURSING": 0.15}) or ["FRAIL"]
        authority = "MINISTRY_OF_HEALTH" if "NURSING" in levels else "MINISTRY_OF_WELFARE"
        moh = "NURSING" in levels and chance(rng, 0.5)
        monthly = round_to(10000 * price_factor, 250)
        monthly_max = monthly + round_to(rng.uniform(1000, 4000), 250)
        deposit = None
        couples = pick(rng, {"NO": 30, "SAME_LEVEL": 50, "MIXED_LEVELS": 20})
        units = subset(rng, {"GERIATRIC_REHAB": 0.05})
        ventilated = "NO"
        wandering = "YES" if "COGNITIVE_FRAIL" in levels and chance(rng, 0.6) else "NO"
        peg = "YES" if "NURSING" in levels and chance(rng, 0.5) else "NO"
        ng = "YES" if "NURSING" in levels and chance(rng, 0.3) else "NO"
        nurse = "YES" if "NURSING" in levels or chance(rng, 0.4) else "NO"
    else:  # protected housing
        has_ward = chance(rng, 0.35)
        levels = ["INDEPENDENT"] + subset(rng, {"FRAIL": 0.5}) + (["NURSING"] if has_ward else [])
        levels += ["COGNITIVE_FRAIL"] if has_ward and chance(rng, 0.3) else []
        authority = "MINISTRY_OF_HEALTH" if has_ward else "MINISTRY_OF_WELFARE"
        moh = has_ward and chance(rng, 0.3)
        model = pick(rng, {"FULL_DEPOSIT": 55, "PARTIAL_DEPOSIT": 25, "RENTAL": 20})
        if model == "FULL_DEPOSIT":
            deposit = round_to(rng.uniform(500_000, 1_500_000) * REGION_PRICE[region] * (1.6 if chance(rng, 0.15) else 1), 10_000)
            monthly = round_to(rng.uniform(3500, 7500) * REGION_PRICE[region], 100)
        elif model == "PARTIAL_DEPOSIT":
            deposit = round_to(rng.uniform(200_000, 500_000), 10_000)
            monthly = round_to(rng.uniform(4000, 10000) * REGION_PRICE[region], 100)
        else:
            deposit = None
            monthly = round_to(rng.uniform(10000, 18000) * REGION_PRICE[region], 250)
        monthly_max = monthly + round_to(rng.uniform(500, 3000), 100)
        couples = "MIXED_LEVELS" if has_ward else pick(rng, {"SAME_LEVEL": 70, "MIXED_LEVELS": 30})
        # Supportive unit ("דיור מוגן פלוס"); some such places do not also tick FRAIL,
        # which exercises the rule that the unit itself serves frail residents.
        units = ["SUPPORTIVE"] if chance(rng, 0.4) else []
        ventilated = "NO"
        wandering = "YES" if "COGNITIVE_FRAIL" in levels else "NO"
        peg = "YES" if has_ward and chance(rng, 0.5) else "NO"
        ng = "YES" if has_ward and chance(rng, 0.3) else "NO"
        nurse = "YES" if has_ward or chance(rng, 0.6) else "NO"

    tracks = {"PRIVATE"}
    if moh:
        tracks.add("MOH_CODE")
    if setting == "IL_WELFARE_HOME" and chance(rng, 0.7):
        tracks.add("WELFARE")
    if setting != "IL_PROTECTED_HOUSING" or "NURSING" in levels:
        tracks |= set(subset(rng, {"LTC_INSURANCE": 0.5, "HOLOCAUST_SURVIVORS": 0.3, "MOD": 0.15}))

    if arab:
        languages = ["AR", "HE"] + subset(rng, {"EN": 0.3})
    else:
        languages = ["HE"] + subset(rng, {"RU": 0.55, "AR": 0.3, "EN": 0.4, "AM": 0.08, "FR": 0.1, "ES": 0.08, "RO": 0.06})
        if community == "HAREDI" and chance(rng, 0.6):
            languages.append("YI")

    kashrut = {
        "HAREDI": "MEHADRIN",
        "RELIGIOUS": pick(rng, {"MEHADRIN": 60, "KOSHER": 40}),
        "TRADITIONAL": pick(rng, {"KOSHER": 85, "MEHADRIN": 15}),
        "MIXED": pick(rng, {"KOSHER": 85, "NONE": 15}),
        "SECULAR": pick(rng, {"KOSHER": 65, "NONE": 35}),
    }.get(community, "NONE")
    shabbat = {
        "HAREDI": "OBSERVED",
        "RELIGIOUS": "OBSERVED",
        "TRADITIONAL": pick(rng, {"OBSERVED": 50, "PARTIAL": 50}),
        "MIXED": pick(rng, {"PARTIAL": 70, "NOT": 30}),
        "SECULAR": pick(rng, {"PARTIAL": 30, "NOT": 70}),
    }.get(community)

    shelter = pick(rng, {"ROOM": 30, "FLOOR": 35, "BUILDING": 25, "NEARBY": 10})
    vacancy = {level: pick(rng, {"AVAILABLE_NOW": 25, "WITHIN_MONTH": 20, "WAITLIST": 40, "NONE": 15}) for level in levels}
    phone_area = {"CENTER": "03", "NORTH": "04", "SOUTH": "08"}[region]
    answers = {
        "street_address": f"רחוב לדוגמה {number}, {city}",
        "contact_name": f"איש קשר סינתטי {number}",
        "contact_phone": f"{phone_area}-555{number:04d}",
        "payment_tracks": sorted(tracks),
        "staff_languages": sorted(set(languages)),
        "special_units": units,
        "min_age": 60 if setting == "IL_PROTECTED_HOUSING" else rng.choice([60, 65, 70]),
        "couples": couples,
        "same_gender_care": "YES" if chance(rng, 0.85 if community in {"RELIGIOUS", "HAREDI", "MUSLIM", "DRUZE"} or arab else 0.55) else "NO",
        "beds_total": rng.randint(40, 320),
        "vacancy_by_level": vacancy,
        "short_stays": subset(rng, {"RESPITE": 0.35, "RECOVERY": 0.3 if setting == "IL_NURSING_HOME" else 0.05, "TRIAL": 0.25}),
        "price_includes": subset(rng, {"MEALS": 0.95, "LAUNDRY": 0.8, "CLEANING": 0.85, "ACTIVITIES": 0.8, "MEDICATIONS": 0.3, "NURSING_ON_CALL": 0.5}),
        "nurse_24_7": nurse,
        "physician_presence": pick(rng, {"DAILY": 40, "WEEKLY": 40, "ON_CALL": 20}) if setting == "IL_NURSING_HOME" else pick(rng, {"WEEKLY": 40, "ON_CALL": 50, "NONE": 10}),
        "geriatrician": "YES" if chance(rng, 0.55 if setting == "IL_NURSING_HOME" else 0.2) else "NO",
        "accepts_ventilated": ventilated,
        "wandering_safe": wandering,
        "accepts_peg": peg,
        "accepts_ng_tube": ng,
        "clinical_capabilities": subset(rng, {
            "OXYGEN": 0.8 if setting == "IL_NURSING_HOME" else 0.3,
            "IV": 0.4 if setting == "IL_NURSING_HOME" else 0.05,
            "INSULIN": 0.9,
            "CATHETER": 0.75 if setting == "IL_NURSING_HOME" else 0.2,
            "TRACHEOSTOMY": 0.15 if setting == "IL_NURSING_HOME" else 0.0,
            "PRESSURE_ULCERS": 0.85 if setting == "IL_NURSING_HOME" else 0.2,
            "DIALYSIS_ACCESS": 0.3,
            "BEHAVIORAL": 0.4 if "COGNITIVE_FRAIL" in levels else 0.05,
            "PALLIATIVE": 0.35 if setting == "IL_NURSING_HOME" else 0.05,
        }),
        "therapies": subset(rng, {"PHYSIO": 0.85, "OCCUPATIONAL": 0.6, "SPEECH": 0.25, "DIETITIAN": 0.7, "SOCIAL_WORKER": 0.9, "PSYCHOLOGIST": 0.2}),
        "hospital_minutes": rng.randint(5, 45),
        "religious_character": community,
        "kashrut": kashrut,
        "religious_services": subset(rng, {"SYNAGOGUE": 0.7 if not arab else 0.0, "PRAYER_ROOM": 0.5 if arab else 0.1, "CLERGY": 0.4}),
        "diets": subset(rng, {"DIABETIC": 0.95, "TEXTURE_MODIFIED": 0.85 if "NURSING" in levels else 0.3, "VEGETARIAN": 0.6, "GLUTEN_FREE": 0.3, "LOW_SALT": 0.7}),
        "room_types": (
            subset(rng, {"COUPLE_UNIT": 0.5}) + ["APARTMENT"]
            if setting == "IL_PROTECTED_HOUSING"
            else ["SHARED_2"] + subset(rng, {"SINGLE": 0.6, "SHARED_3PLUS": 0.35, "COUPLE_UNIT": 0.25})
        ),
        "private_bathroom": pick(rng, {"ALL": 55, "SOME": 35, "NONE": 10}) if setting != "IL_PROTECTED_HOUSING" else "ALL",
        "in_room": sorted({"AC"} | set(subset(rng, {"KITCHENETTE": 0.9 if setting == "IL_PROTECTED_HOUSING" else 0.05, "BALCONY": 0.4, "OWN_FURNITURE": 0.5}))),
        "shelter": shelter,
        "shelter_minutes": {"ROOM": 0, "FLOOR": rng.choice([1, 1, 2]), "BUILDING": rng.choice([2, 3, 4]), "NEARBY": rng.choice([3, 5, 7])}[shelter],
        "shelter_bedridden": (
            ("PROTECTED_IN_ROOM" if shelter == "ROOM" else pick(rng, {"MOVED_IN_BED": 75, "NO_SOLUTION": 25}))
            if "NURSING" in levels
            else "NOT_RELEVANT"
        ),
        "accessibility": subset(rng, {"ELEVATOR": 0.92, "WHEELCHAIR": 0.8, "CALL_BUTTON": 0.85}),
        "amenities": subset(rng, {"GARDEN": 0.8, "POOL": 0.25 if setting == "IL_PROTECTED_HOUSING" else 0.05, "GYM": 0.35, "LIBRARY": 0.5, "HAIRDRESSER": 0.6, "CAFE": 0.4, "SHUTTLE": 0.45}),
        "pets": "YES" if chance(rng, 0.25 if setting == "IL_PROTECTED_HOUSING" else 0.05) else "NO",
        "visiting": pick(rng, {"ANYTIME": 60, "SET_HOURS": 40}),
        "family_overnight": "YES" if chance(rng, 0.2) else "NO",
        "family_updates": subset(rng, {"WHATSAPP": 0.7, "PHONE": 0.9, "MEETINGS": 0.6, "APP": 0.15}),
        "setting": pick(rng, {"URBAN": 60, "SUBURBAN": 25, "RURAL": 15}),
        "style": pick(rng, {"LUXURY": 35, "MODERN": 35, "BOUTIQUE": 10, "HOMEY": 20})
        if setting == "IL_PROTECTED_HOUSING"
        else pick(rng, {"LUXURY": 8, "MODERN": 30, "BOUTIQUE": 12, "HOMEY": 50}),
        "day_style": pick(rng, {"STRUCTURED": 45, "FLEXIBLE": 25, "BOTH": 30})
        if setting != "IL_PROTECTED_HOUSING"
        else pick(rng, {"STRUCTURED": 10, "FLEXIBLE": 60, "BOTH": 30}),
        "social_atmosphere": pick(rng, {"LIVELY": 40, "QUIET": 30, "BOTH": 30}),
        "activities_offered": subset(rng, {
            "GARDENING": 0.35, "CRAFTS": 0.6, "GAMES": 0.65, "MUSIC": 0.7, "LECTURES": 0.55,
            "MOVEMENT": 0.75, "OUTINGS": 0.35, "SPIRITUAL": 0.6 if community in {"RELIGIOUS", "HAREDI", "TRADITIONAL"} else 0.15,
        }),
    }
    if shabbat:
        answers["shabbat"] = shabbat
    if setting == "IL_PROTECTED_HOUSING" and deposit:
        answers["deposit_depreciation_pct_per_year"] = round(rng.uniform(2.0, 4.0), 1)
    case, publication, offers = build_offers(rng, setting, levels, monthly, deposit, vacancy)
    answers["price_publication"] = publication
    if offers:
        answers["price_offers"] = offers
    core = {
        "functional_levels_served": sorted(set(levels)),
        "moh_code_agreement": "YES" if moh else "NO",
        "license_authority": authority,
        "license_id": f"SYN-{number:04d}",
        # ~3% expired licences, to exercise the shared LICENSE_CURRENTLY_VALID gate.
        "license_expiration_date": (
            date(2026, rng.randint(1, 10), 1) if chance(rng, 0.03) else date(2026 + rng.choice([1, 2, 3]), 11, 15)
        ).isoformat(),
    }
    return core, answers, case


REQUIRED_ONLY = {"street_address", "contact_name", "contact_phone", "payment_tracks", "staff_languages"}


def build(seed: int):
    rng = random.Random(seed)
    cities = list(CITY_WEIGHTS)
    records, registrations, profile = [], {}, []
    number = 0
    for setting, count, type_label, _ in SETTINGS:
        for _ in range(count):
            number += 1
            city = rng.choices(cities, weights=[CITY_WEIGHTS[c] for c in cities])[0]
            lat, lon, region, communities = CITIES[city]
            community = pick(rng, communities)
            canonical_id = f"IL-SYN-{number:03d}"
            name = f"[סינתטי] {rng.choice(NAME_WORDS)} {rng.choice(NAME_TAILS)} {city} {number:03d}"

            # Registration state mix (assumption): 80% full, 12% only the required
            # answers, 8% never registered (tests "unknown" handling).
            state = pick(rng, {"FULL": 80, "REQUIRED_ONLY": 12, "NOT_REGISTERED": 8})
            core, answers, price_case = build_answers(rng, setting, community, region, number, city)
            if state != "NOT_REGISTERED":
                if state == "REQUIRED_ONLY":
                    answers = {k: v for k, v in answers.items() if k in REQUIRED_ONLY}
                    price_case = "NO_PRICE"
                answers = {k: v for k, v in answers.items() if v not in ([], {}, None, "")}
                payload = validate_registration({**core, "questionnaire": answers})
                payload["prices_verified_at"] = date(2026, 11, rng.randint(1, 14)).isoformat()
                registrations[canonical_id] = payload
            else:
                price_case = "NOT_REGISTERED"

            unknown = {"value": None, "status": "UNKNOWN", "source": None, "basis": "UNKNOWN"}
            records.append({
                "canonical_id": canonical_id,
                "canonical_schema_version": SCHEMA,
                "country": "IL",
                "state": "IL",
                "facility_name": name,
                "city": city,
                "address": f"רחוב לדוגמה {number}, {city}",
                "district": region,
                "phone": None,
                "website": None,
                "latitude": round(lat + rng.uniform(-0.02, 0.02), 5),
                "longitude": round(lon + rng.uniform(-0.02, 0.02), 5),
                "operator_name": "מפעיל סינתטי",
                "ownership_type": None,
                "licensing": {"authority": dict(unknown), "license_id": dict(unknown), "moh_code_agreement": dict(unknown)},
                "pricing": {"currency": "ILS", "monthly_price": dict(unknown), "deposit": dict(unknown), "payment_tracks": dict(unknown)},
                "care_capabilities": {"functional_levels_served": dict(unknown), "departments": dict(unknown)},
                "lifestyle": {"religion_attitude": dict(unknown)},
                "registration_status": "NOT_REGISTERED",
                "matching_eligibility": "NOT_REGISTERED",
                "availability": "UNKNOWN",
                "merge_confidence": "NOT_MERGED",
                "data_quality_flags": ["SYNTHETIC_TEST_DATA"],
                "source_retrieved_at": GENERATED_AT,
                "facility_type": type_label,
                "source_facility_type": None,
                "canonical_setting": setting,
                "source_identity_ids": {"synthetic_seed_row": str(number)},
                "source_evidence": {
                    f"synthetic:{number}": {
                        "source_name": "נתונים סינתטיים לבדיקות (לא מוסד אמיתי)",
                        "source_authority": "OOMNIK test data generator",
                        "source_file": "scripts/generate_israel_synthetic_facilities.py",
                        "source_record_id": str(number),
                        "source_received_date": GENERATED_AT[:10],
                        "source_retrieved_at": GENERATED_AT,
                        "scope": "FACILITY",
                    }
                },
                "synthetic": True,
            })
            profile.append({"setting": setting, "community": community, "region": region, "state": state, "price_case": price_case})
    return records, registrations, profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261115)
    args = parser.parse_args()
    records, registrations, profile = build(args.seed)
    assert len(records) == TOTAL
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    universe = {
        "generated_at_utc": GENERATED_AT,
        "record_count": len(records),
        "canonical_schema_version": SCHEMA,
        "merge_policy": "SYNTHETIC_TEST_DATA_DO_NOT_SHOW_TO_FAMILIES",
        "seed": args.seed,
        "records": records,
    }
    (OUT_DIR / "facility_universe.json").write_text(json.dumps(universe, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "registrations.json").write_text(
        json.dumps({"seed": args.seed, "registrations": registrations}, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    print(f"{len(records)} facilities, {len(registrations)} registered")
    for key in ("setting", "community", "region", "state", "price_case"):
        print(key, dict(Counter(p[key] for p in profile).most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
