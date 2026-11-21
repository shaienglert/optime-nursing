"""Israeli family results route (owner decision 2026-11-17, alternative A).

Hebrew intake -> this route -> Hebrew results -> facility pages -> visit coordination.

The matching itself is the shared engine (client_intent_runtime: MUST gates, NICE
ranking, rank key) and the shared OOMNIKER (oomniker_optimizer), with the Israeli
market rules plugged in (israel_must_gates). This module only orchestrates:

1. Free text goes through the shared AI interpreter into the canonical structured
   profile. Buttons stay authoritative; text that cannot be interpreted is marked
   UNPROCESSED and the family is told -- never guessed.
2. Required Israeli facts (functional level, funding pathway unless complex nursing,
   locality) must be present; otherwise the family is asked, nothing is matched.
3. Every facility in the active universe is evaluated. Only facilities whose hard gate
   is PASS (every MUST satisfied by the facility's own answers) are shown. Facilities
   waiting on missing information are counted and explained, never shown as matches.
4. OOMNIKER explains the narrowing and may suggest verification; it never relaxes a MUST.

Nevada does not use this module.
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

KEY_HE: Dict[str, str] = {
    "IL_NURSING_CONTINUITY": "מחלקה סיעודית באותו מתחם",
    "IL_BEDROOMS": "מספר חדרי השינה הנדרש",
    "IL_PRIVATE_CAREGIVER": "אפשרות להביא מטפל/ת פרטי/ת",
    "IL_PARKING": "סוג החניה הנדרש",
    "IL_PET": "אפשר להביא חיית מחמד",
    "IL_DIETS": "תפריט מותאם לדרישות",

    "LICENSE_CURRENTLY_VALID": "רישיון בתוקף",
    "IL_FUNCTIONAL_LEVEL": "מקבל את רמת התפקוד",
    "IL_MOH_CODE_AGREEMENT": "הסכם קוד עם משרד הבריאות",
    "IL_FUNDING_TRACK": "מקבל את מסלול המימון",
    "IL_ACCEPTS_VENTILATED": "מקבל מונשמים",
    "IL_WANDERING_SAFE": "מחלקה סגורה או השגחה למשוטטים",
    "IL_ACCEPTS_PEG": "מקבל הזנה ב־PEG",
    "IL_ACCEPTS_NG_TUBE": "מקבל זונדה",
    "IL_ACCEPTS_COUPLE": "מקבל זוגות",
    "IL_PSYCHOGERIATRIC_UNIT": "מחלקה פסיכוגריאטרית",
    "IL_SHELTER_MINIMUM": "מרחב מוגן ברמה שביקשתם",
    "IL_BEDRIDDEN_SHELTER": "פתרון מיגון למרותקים למיטה",
    "IL_COMMUNITY": "אופי המוסד",
    "IL_KASHRUT": "כשרות",
    "IL_SHABBAT": "שמירת שבת",
    "IL_SAME_GENDER_CARE": "טיפול אישי מאותו מגדר",
    "IL_LANGUAGE": "שפת הצוות",
    "IL_SHELTER": "ממ\"ד קרוב",
    "IL_BUDGET": "תקציב",
    "IL_AVAILABILITY": "מקום פנוי",
    "IL_DISTANCE": "בטווח המרחק שבחרתם",
    "IL_PROXIMITY": "קרבה",
    "IL_PRIORITY": "מה שהכי חשוב לכם",
    "IL_SETTING": "סביבה",
    "IL_STYLE": "סגנון המקום",
    "IL_DAY_RHYTHM": "סדר היום",
    "IL_ACTIVITIES": "פעילויות",
}

logger = logging.getLogger(__name__)

def label(key: str) -> str:
    base = str(key).split(":", 1)[0]
    return KEY_HE.get(base, base)


def _must_label(must: Dict[str, Any]) -> str:
    key, value = must["key"], must.get("value")
    if key == "IL_BEDROOMS":
        return f"לפחות {value} חדרי שינה נפרדים"
    if key == "IL_PRIVATE_CAREGIVER":
        return {
            "VISITS": "מטפל/ת פרטי/ת שמגיע/ה לביקורים מיום הקליטה",
            "LIVE_IN": "מטפל/ת פרטי/ת שמתגורר/ת עם הדייר/ת מיום הקליטה",
            "UNCLEAR": "מטפל/ת פרטי/ת — סידור מגורים לבירור",
        }[value]
    if key == "IL_PARKING":
        return {"REGULAR": "חניה לדיירים", "ACCESSIBLE": "חניה נגישה", "COVERED": "חניה מקורה"}[value]
    if key == "IL_DIETS":
        from app.services.israel_facility_questionnaire import QUESTIONS

        options = {entry["value"]: entry["label"] for entry in QUESTIONS["diets"]["options"]}
        return "תפריט מותאם: " + ", ".join(options[item] for item in value)
    return label(key)


def _interpreter_configured() -> bool:
    return bool(os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip() and os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip())


UNPROCESSED_MESSAGE = "את מה שכתבתם במלל חופשי לא הצלחנו לעבד כרגע, ולכן הוא לא השפיע על התוצאות. התוצאות מבוססות על התשובות בשאלון."

# What the family sees under "מה הבנו מכם": field label and Hebrew value names.
FIELD_HE = {
    "functionalLevel": "רמת תפקוד", "fundingPathway": "מימון", "monthlyBudgetIls": "תקציב חודשי",
    "depositCapIls": "פיקדון מרבי", "city": "יישוב", "maxDistanceKm": "מרחק מרבי", "medicalNeeds": "צרכים רפואיים",
    "specialUnits": "מחלקה מיוחדת", "isCouple": "זוג", "partnerSameLevel": "אותה רמת תפקוד לשניהם",
    "community": "אופי", "kashrut": "כשרות", "shabbat": "שבת", "sameGenderCare": "טיפול אישי מאותו מגדר",
    "language": "שפה", "shelterNeed": "מרחב מוגן", "shelterIsCondition": "מרחב מוגן כתנאי", "bedridden": "מרותק/ת למיטה",
    "relationship": "קרבה", "requiredDiets": "תזונה", "privateCaregiver": "מטפל/ת פרטי/ת", "priority": "הכי חשוב",
    "setting": "סביבה", "styles": "סגנון", "dayRhythm": "סדר יום", "activities": "פעילויות", "petRequired": "חיית מחמד",
    "parkingType": "חניה", "minBedrooms": "חדרי שינה",
}
VALUE_HE = {
    "INDEPENDENT": "עצמאי/ת", "FRAIL": "תשוש/ה", "NURSING": "סיעודי/ת", "COMPLEX_NURSING": "סיעוד מורכב",
    "COGNITIVE_FRAIL": "תשוש/ת נפש", "UNCLEAR": "עוד לא ידוע", "MOH_CODE": "קוד משרד הבריאות",
    "WELFARE_ASSISTANCE": "סיוע משרד הרווחה", "PRIVATE": "פרטי", "VENTILATION": "הנשמה", "WANDERING": "שוטטות / מחלקה סגורה",
    "PEG": "הזנה ב־PEG", "NG_TUBE": "זונדה", "PSYCHOGERIATRIC": "פסיכוגריאטרית", "SECULAR": "חילוני", "TRADITIONAL": "מסורתי",
    "RELIGIOUS": "דתי", "HAREDI": "חרדי", "MUSLIM": "מוסלמי", "CHRISTIAN": "נוצרי", "DRUZE": "דרוזי", "KOSHER": "כשר",
    "MEHADRIN": "כשר מהדרין", "IMPORTANT": "חשוב", "HE": "עברית", "RU": "רוסית", "AR": "ערבית", "EN": "אנגלית", "AM": "אמהרית",
    "YI": "יידיש", "FR": "צרפתית", "ES": "ספרדית", "RO": "רומנית",
    "LUXURY": "יוקרתי", "MODERN": "מודרני", "BOUTIQUE": "בוטיק", "HOMEY": "ביתי", "URBAN": "עירונית", "RURAL": "כפרית",
    "GARDENING": "גינון", "CRAFTS": "יצירה", "GAMES": "משחקים", "MUSIC": "מוזיקה", "LECTURES": "הרצאות", "MOVEMENT": "תנועה",
    "OUTINGS": "יציאות", "SPIRITUAL": "רוחניות", "MEDICAL": "טיפול רפואי", "SOCIAL": "חיי חברה", "SAFETY": "בטיחות",
    "PEACE_OF_MIND": "שקט נפשי", "PRIVATE_SPACE": "פרטיות", "PEOPLE_AROUND": "אנשים מסביב", "STRUCTURED": "סדר יום קבוע",
    "FLEXIBLE": "סדר יום גמיש", "DIABETIC": "סוכרתי", "TEXTURE_MODIFIED": "מרקם מותאם", "VEGETARIAN": "צמחוני",
    "GLUTEN_FREE": "ללא גלוטן", "LOW_SALT": "דל מלח", "VEGAN": "טבעוני", "HALAL": "חלאל", "VISITS": "מגיע/ה לביקורים",
    "LIVE_IN": "מתגורר/ת", "REGULAR": "רגילה", "ACCESSIBLE": "נגישה", "COVERED": "מקורה", "ROOM": "ממ\"ד בחדר", "FLOOR": "מרחב מוגן בקומה",
}
IMPORTANCE_HE = {"MUST": "חובה", "NICE": "רצוי", "CONTEXT": "רקע", "UNKNOWN": "לא ברור"}


def _value_he(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "כן" if value else "לא"
    if isinstance(value, list):
        return ", ".join(_value_he(key, v) for v in value)
    if key in {"monthlyBudgetIls", "depositCapIls"} and isinstance(value, (int, float)):
        return f"{int(value):,} ₪"
    if key == "maxDistanceKm" and isinstance(value, (int, float)):
        return f"{int(value)} ק\"מ"
    return VALUE_HE.get(str(value), str(value))


def _squash(text: Any) -> str:
    return re.sub(r"[\s\"'״׳.,!?]", "", str(text or ""))


def _locality_from(value: Any) -> Optional[str]:
    """A locatable locality from what the interpreter wrote: the name itself, an abbreviation,
    or the first locatable name in a list ("אשדוד או אשקלון")."""
    from app.services.israel_geo import canonical_locality, locate

    text = str(value or "").strip()
    if not text:
        return None
    if locate(text):
        return canonical_locality(text)
    for part in re.split(r"\s+או\s+|,|/|\s+ו(?=[\u0590-\u05FF])", text):
        part = part.strip()
        for candidate in (part, part[1:] if part[:1] in "במלה" and len(part) > 2 else None):
            if candidate and locate(candidate):
                return canonical_locality(candidate)
    return None


def _locality_in_text(text: str) -> Optional[Tuple[str, str]]:
    """(locality, words) for the first Israeli locality written in the family text."""
    from app.services.israel_geo import canonical_locality, locate

    tokens = re.findall(r"[\u0590-\u05FF\"'״׳\-]+", text or "")
    for i in range(len(tokens)):
        for n in (3, 2, 1):
            words = " ".join(tokens[i:i + n])
            if len(tokens[i:i + n]) < n:
                continue
            for candidate in (words, words[1:] if words[:1] in "במלה" and len(words) > 2 else None):
                if candidate and len(candidate) > 1 and locate(candidate):
                    return canonical_locality(candidate), words
    return None


def _call_interpreter(text: str, questionnaire_state: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.semantic_intent_ai import interpret_client_intent_with_ai

    try:
        return interpret_client_intent_with_ai(user_text=text, questionnaire_state=questionnaire_state)
    except Exception as error:
        # One retry for an invalid model packet (not for transport failures, which the
        # interpreter already retries): a second sample usually validates.
        if "TRANSPORT" in str(error) or "HTTP_4" in str(error):
            raise
        logger.warning("israel_interpreter_retry reason=%s", str(error)[:120])
        return interpret_client_intent_with_ai(user_text=text, questionnaire_state=questionnaire_state)


def interpret(questionnaire_state: Dict[str, Any], text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Buttons + family text -> decision questionnaire, through the shared interpreter."""
    text = (text or "").strip()
    if not text:
        return questionnaire_state, {"status": "NO_TEXT"}
    if not _interpreter_configured():
        return questionnaire_state, {"status": "UNPROCESSED", "message": UNPROCESSED_MESSAGE}
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

    try:
        result = _call_interpreter(text, questionnaire_state)
    except Exception as error:  # the interpreter must never block the family
        reason = str(error).split(":", 1)[0][:60] or type(error).__name__
        logger.warning("israel_interpreter_failed reason=%s detail=%s", reason, str(error)[:300])
        return questionnaire_state, {"status": "UNPROCESSED", "reason": reason, "message": UNPROCESSED_MESSAGE}
    profile = build_structured_profile(questionnaire_state, result, family_text=text)
    state = materialize_questionnaire(profile)
    for key, value in questionnaire_state.items():
        if key != "israelMarket":
            state.setdefault(key, value)
    israel = state.get("israelMarket")
    if not isinstance(israel, dict):
        israel = state["israelMarket"] = {}
    buttons = questionnaire_state.get("israelMarket") if isinstance(questionnaire_state.get("israelMarket"), dict) else {}

    understood: List[Dict[str, Any]] = []
    fields = profile.get("fields") or {}
    for path, field in fields.items():
        if not path.startswith("israelMarket.") or field.get("provenance") != "AI_EXTRACTED" or field.get("state") != "EXPLICIT":
            continue
        key = path.split(".", 1)[1]
        if key not in israel or key not in FIELD_HE:
            continue
        understood.append({"field": key, "label": FIELD_HE[key], "value": israel[key], "value_he": _value_he(key, israel[key]), "quote": field.get("quote"), "basis": "TEXT"})

    # Locality: the questionnaire needs one locatable place. The interpreter sometimes writes
    # two ("אשדוד או אשקלון"), an abbreviation, or nothing for "5 ק"מ מקריית שמונה".
    if not str(buttons.get("city") or "").strip():
        written = israel.get("city")
        located = _locality_from(written)
        if located and located != written:
            israel["city"] = located
            for row in understood:
                if row["field"] == "city":
                    row.update(value=located, value_he=located, basis="TEXT_FIRST_LOCALITY")
        elif not located:
            found = _locality_in_text(text)
            if found:
                israel["city"] = found[0]
                understood = [r for r in understood if r["field"] != "city"]
                understood.append({"field": "city", "label": FIELD_HE["city"], "value": found[0], "value_he": found[0], "quote": found[1], "basis": "TEXT_LOCALITY_MATCH"})

    # "כשר" is kashrut, never a halal diet: keep HALAL only when the family wrote it.
    diets = israel.get("requiredDiets")
    if isinstance(diets, list) and "HALAL" in diets and not re.search(r"חלאל|halal|حلال", text, re.I):
        israel["requiredDiets"] = [d for d in diets if d != "HALAL"]
        if not israel["requiredDiets"]:
            israel.pop("requiredDiets")
        understood = [u for u in understood if u["field"] != "requiredDiets"] + (
            [{"field": "requiredDiets", "label": FIELD_HE["requiredDiets"], "value": israel["requiredDiets"], "value_he": _value_he("requiredDiets", israel["requiredDiets"]), "quote": None, "basis": "TEXT"}]
            if israel.get("requiredDiets") else []
        )

    # A monthly budget with no MoH code or welfare mentioned means paying privately. Shown
    # as an inference so the family can correct it.
    if (
        not str(buttons.get("fundingPathway") or "").strip()
        and not str(israel.get("fundingPathway") or "").strip()
        and isinstance(israel.get("monthlyBudgetIls"), (int, float)) and israel["monthlyBudgetIls"] > 0
        and not re.search(r"קוד|רווחה|משרד הבריאות", text)
    ):
        israel["fundingPathway"] = "PRIVATE"
        understood.append({"field": "fundingPathway", "label": FIELD_HE["fundingPathway"], "value": "PRIVATE", "value_he": "פרטי", "quote": None, "basis": "INFERRED_FROM_BUDGET"})

    # Everything the family wrote that has no field is shown, never dropped. A requirement
    # (importance MUST) without a field is flagged: we cannot check it for them.
    importance = {str(s.get("raw_text") or "").strip(): str(s.get("importance") or "UNKNOWN").upper() for s in result.get("statements") or [] if isinstance(s, dict)}
    not_used: List[Dict[str, Any]] = []
    seen = set()
    used_quotes = [_squash(u.get("quote")) for u in understood if u.get("quote")]
    for item in profile.get("out_of_schema") or []:
        quote = str(item.get("quote") or item.get("text") or "").strip()
        if not quote or quote in seen:
            continue
        squashed = _squash(quote)
        if any(q and (q in squashed or squashed in q) for q in used_quotes):
            continue  # this sentence was used for a field shown under "מה הבנו"
        seen.add(quote)
        level = importance.get(quote, "UNKNOWN")
        not_used.append({"text": quote, "importance": level, "importance_he": IMPORTANCE_HE.get(level, "לא ברור")})

    order = list(FIELD_HE)
    understood.sort(key=lambda r: order.index(r["field"]) if r["field"] in order else 99)
    question = result.get("next_question")
    if question and not re.search(r"[\u0590-\u05FF]", str(question)):
        question = None  # the family is asked in Hebrew only; a missing item gets a Hebrew question below
    return state, {
        "status": "INTERPRETED",
        "conflicts": profile.get("conflicts") or [],
        "unprocessed": profile.get("unprocessed") or [],
        "clarification_question": question,
        "understood": understood,
        "understood_state": {r["field"]: r["value"] for r in understood},
        "not_used": not_used,
        "unchecked_requirements": [n["text"] for n in not_used if n["importance"] == "MUST"],
    }


MISSING_QUESTION_HE = {
    "functionalLevel": "מה המצב התפקודי היום: עצמאי/ת, תשוש/ה, סיעודי/ת, סיעוד מורכב, תשוש/ת נפש, או שעוד לא ידוע?",
    "fundingPathway": "איך מתכננים לממן: קוד של משרד הבריאות, סיוע של משרד הרווחה, תשלום פרטי (ואם כן, עד כמה בחודש), או שעוד לא ידוע?",
    "city": "באיזה יישוב בישראל לחפש?",
}


def missing_required(israel: Dict[str, Any]) -> List[str]:
    level = str(israel.get("functionalLevel") or "").strip()
    missing = []
    unit_defines_setting = "PSYCHOGERIATRIC" in {str(u).upper() for u in israel.get("specialUnits") or []}
    if not level and not unit_defines_setting:
        missing.append("functionalLevel")
    if level.upper() != "COMPLEX_NURSING" and not str(israel.get("fundingPathway") or "").strip():
        missing.append("fundingPathway")
    from app.services.israel_geo import locate

    if not locate(str(israel.get("city") or "").strip()):
        missing.append("city")
    return missing


def _card(record: Dict[str, Any], fit: Dict[str, Any], registration: Optional[Dict[str, Any]], rank: int, must_labels: Dict[str, str]) -> Dict[str, Any]:
    from app.services.israel_facility_questionnaire import describe_offer, price_display

    notes = fit.get("israel_notes") or {}
    budget = notes.get("IL_BUDGET") or {}
    explained_nice = [k for k in fit.get("nice_match") or [] if k != "IL_PROXIMITY"]
    return {
        "rank": rank,
        "canonical_id": record["canonical_id"],
        "name": record.get("facility_name"),
        "facility_type": record.get("facility_type"),
        "city": record.get("city"),
        "distance_km": fit.get("distance_km"),
        "musts_met": [{"key": k, "label": must_labels.get(k, label(k))} for k in fit.get("must_pass") or []],
        "preferences_met": [{"key": k, "label": label(k)} for k in explained_nice],
        "preferences_not_met": [{"key": k, "label": label(k)} for k in fit.get("nice_mismatch") or []],
        "unknown": [{"key": k, "label": label(k)} for k in fit.get("nice_unknown") or []],
        "budget": {"label": budget.get("label"), "offer": describe_offer(budget["offer"]) if budget.get("offer") else None} if budget else None,
        "prices": price_display(registration),
        "source": {
            "basis": "FACILITY_SUPPLIED",
            "label": "המידע נמסר על ידי המוסד",
            "updated_at": (registration or {}).get("prices_verified_at"),
        },
        "rank_key": list(_rank_key(fit)),
    }


def _rank_key(fit: Dict[str, Any]) -> Tuple:
    from app.services.client_intent_runtime import intent_rank_key

    return tuple(intent_rank_key({"client_intent_fit": fit}))


def _oomniker_he(analysis: Dict[str, Any], facility_pending: int, fail: Counter, pending: Counter, shown: int, family_unknown: List[str]) -> Dict[str, Any]:
    """Hebrew wording of the shared OOMNIKER analysis. Never suggests relaxing a MUST.

    A MUST the family itself left open ("not sure") is the family's question, not
    missing facility information, so it is never attributed to the facilities."""
    lines: List[str] = []
    actions: List[str] = []
    if "IL_FUNCTIONAL_LEVEL" in family_unknown:
        lines.append("סימנתם שרמת התפקוד עוד לא ברורה. בלי זה אי אפשר לדעת אילו מקומות יכולים לקבל אותו, ולכן לא מוצגות התאמות.")
        actions.append("אפשר לחזור לשאלון ולבחור את הרמה הקרובה ביותר. ליד כל רמה יש הסבר קצר. אם עדיין לא בטוחים, רופא המשפחה או עובד/ת סוציאלי/ת יכולים לעזור לקבוע.")
    if shown == 0:
        lines.append("אין כרגע מוסד שעומד בכל תנאי החובה שלכם.")
    if fail:
        top = ", ".join(f"{label(k)} ({n})" for k, n in fail.most_common(3))
        lines.append(f"מוסדות שלא מוצגים כי לא עומדים בתנאי חובה: {top}.")
    if pending:
        top = ", ".join(f"{label(k)} ({n})" for k, n in pending.most_common(3))
        lines.append(f"{facility_pending} מוסדות נוספים עוד לא מסרו מידע על: {top}. הם לא מוצגים כהתאמה עד שיאשרו.")
    if any(s.get("action") == "VERIFY_WITH_COMMUNITIES" for s in analysis.get("suggestions") or []):
        actions.append("אפשר שנפנה למוסדות שחסר אצלם מידע ונבקש מהם להשלים.")
    if shown == 0:
        actions.append("תנאי החובה שלכם לא משתנים. ההעדפות (מרחק, אופי, שפה ועוד) לא מסננות מוסדות, רק משנות את הסדר, ולכן שינוי שלהן לא יוסיף התאמות.")
    return {"lines": lines, "actions": actions, "analysis": analysis}


def build_israel_results(db: Session, questionnaire_state: Dict[str, Any], natural_language_query: str = "", limit: int = 20) -> Dict[str, Any]:
    from app.models.facility import Facility, FacilityPhoto
    from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
    from app.services.israel_facility_import import load_israel_records
    from app.services.israel_facility_registration import load_israel_registration
    from app.services.oomniker_optimizer import analyze_oomniker

    text = natural_language_query or str(questionnaire_state.get("notes") or "")
    state, interpretation = interpret(questionnaire_state, text)
    israel = state.get("israelMarket") if isinstance(state.get("israelMarket"), dict) else {}
    if israel.get("privateCaregiver") == "UNCLEAR":
        interpretation["clarification_question"] = "האם המטפל/ת הפרטי/ת מגיע/ה לביקורים או מתגורר/ת עם הדייר/ת?"
    missing = missing_required(israel)
    if missing:
        # Never leave the family stuck without a question: ask for the first missing item.
        if not str(interpretation.get("clarification_question") or "").strip():
            interpretation["clarification_question"] = MISSING_QUESTION_HE.get(missing[0])
        written_city = str(israel.get("city") or "").strip()
        if "city" in missing and written_city:
            interpretation["city_unrecognized"] = written_city
            interpretation["clarification_question"] = f"לא זיהינו את היישוב \"{written_city}\". באיזה יישוב בישראל לחפש?"
        return {"status": "NEEDS_INPUT", "missing": missing, "interpretation": interpretation, "results": []}

    # A budget question is noise when the code, welfare or complex nursing already covers funding.
    question = str(interpretation.get("clarification_question") or "")
    covered = str(israel.get("fundingPathway") or "").upper() in {"MOH_CODE", "WELFARE_ASSISTANCE"} or str(israel.get("functionalLevel") or "").upper() == "COMPLEX_NURSING"
    if covered and re.search(r"תקציב|מימון|לממן|פרטי", question):
        interpretation["clarification_question"] = None

    intent = build_client_intent({"israelMarket": israel}, text, {}, {})
    records, generated_at = load_israel_records()
    evaluated = [(record, evaluate_candidate_intent(record, intent)) for record in records]

    # MUSTs the family left open; their unknowns belong to the family, not the facilities.
    family_unknown = ["IL_FUNCTIONAL_LEVEL"] if str(israel.get("functionalLevel") or "").upper() == "UNCLEAR" else []
    if israel.get("privateCaregiver") == "UNCLEAR":
        family_unknown.append("IL_PRIVATE_CAREGIVER")
    gates = Counter(fit["hard_gate"] for _, fit in evaluated)
    fail = Counter(k for _, fit in evaluated if fit["hard_gate"] == "FAIL" for k in fit.get("must_fail") or [])
    pending = Counter(
        k for _, fit in evaluated if fit["hard_gate"] == "PENDING_VERIFICATION" for k in fit.get("must_unknown") or [] if k not in family_unknown
    )
    facility_pending = sum(
        1 for _, fit in evaluated
        if fit["hard_gate"] == "PENDING_VERIFICATION" and any(k not in family_unknown for k in fit.get("must_unknown") or [])
    )
    passing = sorted((item for item in evaluated if item[1]["hard_gate"] == "PASS"), key=lambda item: _rank_key(item[1]))

    shown = passing[:limit]
    must_labels = {must["key"]: _must_label(must) for must in intent.get("must_haves") or []}
    shown_ids = [record["canonical_id"] for record, _ in shown]
    photos: Dict[str, Dict[str, Any]] = {}
    if shown_ids:
        for canonical_id, url, caption in (
            db.query(Facility.cms_id, FacilityPhoto.url, FacilityPhoto.caption)
            .join(FacilityPhoto, FacilityPhoto.facility_id == Facility.id)
            .filter(Facility.cms_id.in_(shown_ids), FacilityPhoto.is_active.is_(True))
            .order_by(FacilityPhoto.uploaded_at, FacilityPhoto.id)
        ):
            photos.setdefault(canonical_id, {"url": url, "caption": caption})
    cards = [
        {
            **_card(record, fit, load_israel_registration(db, record["canonical_id"]), rank, must_labels),
            "photo": photos.get(record["canonical_id"]),
        }
        for rank, (record, fit) in enumerate(shown, 1)
    ]

    ledger = [
        {
            "canonical_facility_id": record["canonical_id"],
            "must_fail": fit.get("must_fail") or [],
            "must_unknown": [k for k in fit.get("must_unknown") or [] if k not in family_unknown],
        }
        for record, fit in evaluated
    ]
    analysis = analyze_oomniker({}, [{"canonical_facility_id": c["canonical_id"]} for c in cards], decision_context={"ledger": ledger, "client_intent": intent, "funnel": {}})

    return {
        "status": "OK",
        "interpretation": interpretation,
        "musts": [{"key": m["key"], "label": _must_label(m)} for m in intent.get("must_haves") or []],
        "preferences": [{"key": n["key"], "label": label(n["key"])} for n in intent.get("nice_to_haves") or [] if str(n.get("key", "")).startswith("IL_") and n["key"] != "IL_PROXIMITY"],
        "funnel": {
            "universe": len(evaluated),
            "passed": gates.get("PASS", 0),
            "pending": gates.get("PENDING_VERIFICATION", 0),
            "pending_on_facility_information": facility_pending,
            "family_unknown": [{"key": k, "label": label(k)} for k in family_unknown],
            "failed": gates.get("FAIL", 0),
            "fail_reasons": [{"key": k, "label": label(k), "count": n} for k, n in fail.most_common()],
            "pending_reasons": [{"key": k, "label": label(k), "count": n} for k, n in pending.most_common()],
            "shown": len(cards),
        },
        "results": cards,
        "oomniker": _oomniker_he(analysis, facility_pending, fail, pending, len(cards), family_unknown),
        "universe_generated_at": generated_at,
    }
