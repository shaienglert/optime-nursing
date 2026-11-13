"""The questionnaire an Israeli facility fills in about itself (portal, Hebrew).

One schema drives both the portal form and validation, so the two cannot drift.
Core questions (functional levels, MoH agreement, licence, prices) keep their
original top-level keys because the shared engine's MUST gates read them. Every
other answer is stored under ``questionnaire`` in the same registration record.

Matching use (governance, AGENTS.md): only the two owner-approved MUST gates read
these answers today (functional level and funding pathway). The other answers are
collected and shown on the facility's page; using any of them to filter or rank is
a product decision that needs owner approval first. An unanswered question is
UNKNOWN, never a "no".
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

LEVEL_OPTIONS = [
    ("INDEPENDENT", "עצמאיים"),
    ("FRAIL", "תשושים"),
    ("NURSING", "סיעודיים"),
    ("COGNITIVE_FRAIL", "תשושי נפש"),
]
VACANCY_OPTIONS = [
    ("AVAILABLE_NOW", "יש מקום עכשיו"),
    ("WITHIN_MONTH", "יתפנה מקום בתוך חודש"),
    ("WAITLIST", "רשימת המתנה"),
    ("NONE", "אין קבלה כרגע"),
]


def _q(key: str, label: str, kind: str, **extra: Any) -> Dict[str, Any]:
    question = {"key": key, "label": label, "type": kind, "required": False, "core": False}
    question.update(extra)
    if "options" in question:
        question["options"] = [{"value": v, "label": l} for v, l in question["options"]]
    return question


SECTIONS: List[Dict[str, Any]] = [
    {
        "key": "contact",
        "title": "פרטי קשר וכתובת",
        "intro": "הכתובת משמשת לחישוב המרחק מהמשפחה. הטלפון מוצג למשפחות שמתעניינות.",
        "questions": [
            _q("street_address", "כתובת מלאה (רחוב ומספר, עיר)", "text", required=True, max_length=200),
            _q("contact_name", "שם איש/אשת הקשר למשפחות", "text", required=True, max_length=120),
            _q("contact_role", "תפקיד", "text", max_length=120),
            _q("contact_phone", "טלפון למשפחות", "phone", required=True),
            _q("contact_email", "דוא\"ל למשפחות", "email"),
            _q("website", "אתר אינטרנט", "url"),
        ],
    },
    {
        "key": "population",
        "title": "קהל יעד ורישוי",
        "intro": "על פי התשובות כאן OOMNIK מחליט לאילו משפחות להציג את המוסד.",
        "questions": [
            _q("functional_levels_served", "אילו אוכלוסיות המוסד מקבל?", "multi", required=True, core=True, options=LEVEL_OPTIONS),
            _q(
                "special_units",
                "מחלקות או יחידות מיוחדות",
                "multi",
                options=[
                    ("COMPLEX_NURSING", "סיעוד מורכב"),
                    ("VENTILATION", "מונשמים"),
                    ("LOCKED_DEMENTIA", "מחלקה סגורה לתשושי נפש"),
                    ("PSYCHOGERIATRIC", "פסיכוגריאטריה"),
                    ("GERIATRIC_REHAB", "שיקום גריאטרי"),
                    ("HOSPICE", "הוספיס / טיפול תומך"),
                ],
            ),
            _q("moh_code_agreement", "האם יש למוסד הסכם קוד עם משרד הבריאות?", "single", required=True, core=True, options=[("YES", "כן"), ("NO", "לא")]),
            _q(
                "license_authority",
                "הגוף המרשה",
                "single",
                required=True,
                core=True,
                options=[("MINISTRY_OF_HEALTH", "משרד הבריאות"), ("MINISTRY_OF_WELFARE", "משרד הרווחה")],
            ),
            _q("license_id", "מספר רישיון", "text", required=True, core=True, max_length=60),
            _q("license_expiration_date", "תוקף הרישיון עד", "date", required=True, core=True),
            _q("min_age", "גיל מינימלי לקבלה", "int", min=0, max=120),
            _q(
                "couples",
                "האם מתקבלים זוגות?",
                "single",
                options=[
                    ("NO", "לא"),
                    ("SAME_LEVEL", "כן, כששניהם באותה רמת תפקוד"),
                    ("MIXED_LEVELS", "כן, גם ברמות תפקוד שונות"),
                ],
            ),
            _q(
                "gender_policy",
                "מגדר",
                "single",
                options=[("MIXED", "גברים ונשים"), ("WOMEN_ONLY", "נשים בלבד"), ("MEN_ONLY", "גברים בלבד")],
            ),
            _q("beds_total", "מספר מיטות / יחידות דיור כולל", "int", min=0, max=5000),
        ],
    },
    {
        "key": "availability",
        "title": "זמינות",
        "intro": "כדאי לעדכן כשמשהו משתנה. ליד כל תשובה נשמר התאריך שבו עודכנה.",
        "questions": [
            _q("vacancy_by_level", "זמינות לפי אוכלוסייה", "per_level", options=VACANCY_OPTIONS),
            _q(
                "short_stays",
                "שהיות קצרות",
                "multi",
                options=[
                    ("RESPITE", "שהיית הפוגה למשפחה"),
                    ("RECOVERY", "החלמה אחרי אשפוז"),
                    ("TRIAL", "תקופת ניסיון לפני מעבר"),
                ],
            ),
        ],
    },
    {
        "key": "funding",
        "title": "מימון ומחירים",
        "intro": "המחירים מוצגים למשפחות כטווח. אפשר להשאיר ריק.",
        "questions": [
            _q(
                "payment_tracks",
                "אילו מסלולי מימון המוסד מקבל?",
                "multi",
                required=True,
                options=[
                    ("PRIVATE", "פרטי"),
                    ("MOH_CODE", "קוד משרד הבריאות"),
                    ("WELFARE", "מימון משרד הרווחה"),
                    ("LTC_INSURANCE", "ביטוח סיעודי"),
                    ("HOLOCAUST_SURVIVORS", "גופי סיוע לניצולי שואה"),
                    ("MOD", "משרד הביטחון"),
                ],
            ),
            _q("monthly_price_ils", "מחיר חודשי החל מ- (₪)", "money", core=True),
            _q("monthly_price_max_ils", "מחיר חודשי עד (₪)", "money"),
            _q("deposit_ils", "פיקדון (₪, בדיור מוגן)", "money", core=True),
            _q("deposit_depreciation_pct_per_year", "שחיקת הפיקדון לשנה (%)", "number", min=0, max=100),
            _q("maintenance_fee_ils", "דמי אחזקה חודשיים (₪, בדיור מוגן)", "money"),
            _q(
                "price_includes",
                "מה כלול במחיר החודשי?",
                "multi",
                options=[
                    ("MEALS", "ארוחות"),
                    ("LAUNDRY", "כביסה"),
                    ("CLEANING", "ניקיון החדר"),
                    ("ACTIVITIES", "פעילויות"),
                    ("MEDICATIONS", "תרופות"),
                    ("NURSING_ON_CALL", "אחות זמינה"),
                ],
            ),
        ],
    },
    {
        "key": "medical",
        "title": "טיפול רפואי",
        "intro": "מה המוסד יכול לתת בפועל, היום.",
        "questions": [
            _q("nurse_24_7", "אחות במקום 24 שעות ביממה", "single", options=[("YES", "כן"), ("NO", "לא")]),
            _q(
                "physician_presence",
                "נוכחות רופא",
                "single",
                options=[("DAILY", "כל יום"), ("WEEKLY", "כמה פעמים בשבוע"), ("ON_CALL", "לפי קריאה"), ("NONE", "אין")],
            ),
            _q("geriatrician", "רופא גריאטר בצוות", "single", options=[("YES", "כן"), ("NO", "לא")]),
            _q(
                "clinical_capabilities",
                "טיפולים שהמוסד מסוגל לתת",
                "multi",
                options=[
                    ("OXYGEN", "חמצן"),
                    ("PEG", "הזנה דרך PEG"),
                    ("NG_TUBE", "זונדה"),
                    ("IV", "עירוי תוך-ורידי"),
                    ("INSULIN", "הזרקות אינסולין"),
                    ("CATHETER", "קטטר"),
                    ("TRACHEOSTOMY", "טרכאוסטומיה"),
                    ("PRESSURE_ULCERS", "טיפול בפצעי לחץ"),
                    ("DIALYSIS_ACCESS", "הסעה ומעקב לדיאליזה"),
                    ("WANDERING", "השגחה על משוטטים"),
                    ("BEHAVIORAL", "התמודדות עם הפרעות התנהגות"),
                    ("PALLIATIVE", "טיפול תומך בסוף החיים"),
                ],
            ),
            _q(
                "therapies",
                "אנשי מקצוע במוסד",
                "multi",
                options=[
                    ("PHYSIO", "פיזיותרפיה"),
                    ("OCCUPATIONAL", "ריפוי בעיסוק"),
                    ("SPEECH", "קלינאות תקשורת"),
                    ("DIETITIAN", "דיאטנית"),
                    ("SOCIAL_WORKER", "עובד/ת סוציאלי/ת"),
                    ("PSYCHOLOGIST", "פסיכולוג/ית"),
                ],
            ),
            _q("nearest_hospital", "בית החולים הקרוב", "text", max_length=120),
            _q("hospital_minutes", "דקות נסיעה לבית החולים", "int", min=0, max=300),
        ],
    },
    {
        "key": "culture",
        "title": "שפה, דת ואוכל",
        "intro": "",
        "questions": [
            _q(
                "staff_languages",
                "באילו שפות הצוות מדבר עם הדיירים?",
                "multi",
                required=True,
                options=[
                    ("HE", "עברית"),
                    ("RU", "רוסית"),
                    ("AR", "ערבית"),
                    ("EN", "אנגלית"),
                    ("AM", "אמהרית"),
                    ("YI", "יידיש"),
                    ("FR", "צרפתית"),
                    ("ES", "ספרדית"),
                    ("RO", "רומנית"),
                ],
            ),
            _q(
                "religious_character",
                "אופי המוסד",
                "single",
                options=[
                    ("SECULAR", "חילוני"),
                    ("TRADITIONAL", "מסורתי"),
                    ("RELIGIOUS", "דתי"),
                    ("HAREDI", "חרדי"),
                    ("MIXED", "מעורב"),
                    ("MUSLIM", "מוסלמי"),
                    ("CHRISTIAN", "נוצרי"),
                    ("DRUZE", "דרוזי"),
                ],
            ),
            _q("kashrut", "כשרות", "single", options=[("NONE", "לא כשר"), ("KOSHER", "כשר"), ("MEHADRIN", "כשר למהדרין")]),
            _q("shabbat", "שמירת שבת במוסד", "single", options=[("OBSERVED", "נשמרת"), ("PARTIAL", "חלקית"), ("NOT", "לא")]),
            _q(
                "religious_services",
                "שירותי דת",
                "multi",
                options=[("SYNAGOGUE", "בית כנסת במקום"), ("PRAYER_ROOM", "חדר תפילה"), ("CLERGY", "ביקורי איש דת")],
            ),
            _q(
                "diets",
                "תפריטים מיוחדים",
                "multi",
                options=[
                    ("DIABETIC", "לסוכרתיים"),
                    ("TEXTURE_MODIFIED", "מרקם מותאם (טחון / רך)"),
                    ("VEGETARIAN", "צמחוני"),
                    ("GLUTEN_FREE", "ללא גלוטן"),
                    ("LOW_SALT", "דל מלח"),
                ],
            ),
        ],
    },
    {
        "key": "housing",
        "title": "חדרים ומבנה",
        "intro": "",
        "questions": [
            _q(
                "room_types",
                "סוגי חדרים",
                "multi",
                options=[
                    ("SINGLE", "חדר ליחיד"),
                    ("SHARED_2", "חדר זוגי (שני דיירים)"),
                    ("SHARED_3PLUS", "שלושה דיירים ומעלה"),
                    ("COUPLE_UNIT", "יחידה לבני זוג"),
                    ("APARTMENT", "דירה"),
                ],
            ),
            _q("private_bathroom", "שירותים ומקלחת צמודים", "single", options=[("ALL", "בכל החדרים"), ("SOME", "בחלק מהחדרים"), ("NONE", "משותפים")]),
            _q(
                "in_room",
                "בחדר",
                "multi",
                options=[("AC", "מזגן"), ("KITCHENETTE", "מטבחון"), ("BALCONY", "מרפסת"), ("OWN_FURNITURE", "אפשר להביא רהיטים")],
            ),
            _q(
                "shelter",
                "מיגון",
                "single",
                options=[
                    ("ROOM", "ממ\"ד בחדר"),
                    ("FLOOR", "מרחב מוגן בכל קומה"),
                    ("BUILDING", "מקלט בבניין"),
                    ("NEARBY", "מקלט בסמוך"),
                ],
            ),
            _q(
                "accessibility",
                "נגישות",
                "multi",
                options=[("ELEVATOR", "מעלית"), ("WHEELCHAIR", "נגיש לכיסא גלגלים בכל המבנה"), ("CALL_BUTTON", "לחצן מצוקה בחדר")],
            ),
            _q(
                "amenities",
                "במוסד",
                "multi",
                options=[
                    ("GARDEN", "גינה"),
                    ("POOL", "בריכה"),
                    ("GYM", "חדר כושר"),
                    ("LIBRARY", "ספרייה"),
                    ("HAIRDRESSER", "מספרה"),
                    ("CAFE", "בית קפה"),
                    ("SHUTTLE", "הסעות"),
                ],
            ),
            _q("pets", "מותר להביא חיית מחמד", "single", options=[("YES", "כן"), ("NO", "לא")]),
        ],
    },
    {
        "key": "family",
        "title": "משפחה וביקורים",
        "intro": "",
        "questions": [
            _q("visiting", "שעות ביקור", "single", options=[("ANYTIME", "בכל שעה"), ("SET_HOURS", "בשעות קבועות")]),
            _q("family_overnight", "בן משפחה יכול ללון במקום", "single", options=[("YES", "כן"), ("NO", "לא")]),
            _q(
                "family_updates",
                "איך המשפחה מקבלת עדכונים",
                "multi",
                options=[("WHATSAPP", "וואטסאפ"), ("PHONE", "טלפון"), ("MEETINGS", "פגישות צוות"), ("APP", "אפליקציה")],
            ),
            _q("about", "כמה מילים על המוסד, במילים שלכם", "textarea", max_length=1500),
        ],
    },
]

QUESTIONS: Dict[str, Dict[str, Any]] = {q["key"]: q for s in SECTIONS for q in s["questions"]}
CORE_KEYS = {k for k, q in QUESTIONS.items() if q["core"]}
_PHONE_RE = re.compile(r"^[0-9+\-() ]{7,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def public_schema() -> Dict[str, Any]:
    return {"version": "il-facility-questionnaire-v1", "sections": SECTIONS}


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _option_values(question: Dict[str, Any]) -> set:
    return {o["value"] for o in question.get("options", [])}


def _clean(question: Dict[str, Any], value: Any) -> Any:
    key, kind, label = question["key"], question["type"], question["label"]
    if kind in {"text", "textarea"}:
        text = str(value).strip()
        if len(text) > question.get("max_length", 500):
            raise ValueError(f"{label}: הטקסט ארוך מדי.")
        return text
    if kind == "phone":
        text = str(value).strip()
        if not _PHONE_RE.match(text):
            raise ValueError(f"{label}: מספר טלפון לא תקין.")
        return text
    if kind == "email":
        text = str(value).strip()
        if not _EMAIL_RE.match(text):
            raise ValueError(f"{label}: כתובת דוא\"ל לא תקינה.")
        return text
    if kind == "url":
        text = str(value).strip()
        if not text.startswith(("http://", "https://")):
            text = "https://" + text
        if " " in text or "." not in text:
            raise ValueError(f"{label}: כתובת אתר לא תקינה.")
        return text
    if kind in {"int", "money", "number"}:
        if isinstance(value, bool):
            raise ValueError(f"{label}: יש להזין מספר.")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}: יש להזין מספר.") from error
        low, high = question.get("min", 0), question.get("max")
        if number < low or (high is not None and number > high):
            raise ValueError(f"{label}: המספר מחוץ לטווח.")
        return number if kind == "number" else int(number)
    if kind == "single":
        text = str(value).upper()
        if text not in _option_values(question):
            raise ValueError(f"{label}: תשובה לא מוכרת.")
        return text
    if kind == "multi":
        if not isinstance(value, list):
            raise ValueError(f"{label}: יש לבחור מהרשימה.")
        chosen = sorted({str(v).upper() for v in value})
        unknown = [v for v in chosen if v not in _option_values(question)]
        if unknown:
            raise ValueError(f"{label}: תשובה לא מוכרת.")
        return chosen
    if kind == "per_level":
        if not isinstance(value, dict):
            raise ValueError(f"{label}: מבנה לא תקין.")
        levels = {v for v, _ in LEVEL_OPTIONS}
        out = {}
        for level, answer in value.items():
            if _empty(answer):
                continue
            if level not in levels or str(answer).upper() not in _option_values(question):
                raise ValueError(f"{label}: תשובה לא מוכרת.")
            out[level] = str(answer).upper()
        return out
    if kind == "date":
        return str(value)
    raise ValueError(f"Unsupported question type for {key}.")


def validate_questionnaire(answers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the non-core answers. Unknown keys are refused; empty answers are dropped
    (they stay UNKNOWN rather than being stored as a negative)."""
    answers = answers or {}
    if not isinstance(answers, dict):
        raise ValueError("questionnaire must be an object.")
    out: Dict[str, Any] = {}
    for key, value in answers.items():
        question = QUESTIONS.get(key)
        if question is None or question["core"]:
            raise ValueError(f"Unknown questionnaire field '{key}'.")
        if _empty(value):
            continue
        cleaned = _clean(question, value)
        if not _empty(cleaned):
            out[key] = cleaned
    missing = [q["label"] for q in QUESTIONS.values() if q["required"] and not q["core"] and q["key"] not in out]
    if missing:
        raise ValueError("חסרות תשובות חובה: " + ", ".join(missing))
    return out


def display_answers(questionnaire: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Answered questions with Hebrew labels, grouped by section, for the facility page."""
    if not questionnaire:
        return []
    level_labels = dict(LEVEL_OPTIONS)
    sections = []
    for section in SECTIONS:
        items = []
        for question in section["questions"]:
            if question["core"] or question["key"] not in questionnaire:
                continue
            value = questionnaire[question["key"]]
            labels = {o["value"]: o["label"] for o in question.get("options", [])}
            if question["type"] == "multi":
                shown = ", ".join(labels.get(v, v) for v in value)
            elif question["type"] == "single":
                shown = labels.get(value, value)
            elif question["type"] == "per_level":
                shown = "; ".join(f"{level_labels.get(k, k)}: {labels.get(v, v)}" for k, v in value.items())
            elif question["type"] == "money":
                shown = f"₪{value:,}"
            elif question["type"] == "number" and question["key"].endswith("_pct_per_year"):
                shown = f"{value:g}%"
            else:
                shown = str(value)
            label = re.sub(r"\s*\((?:₪|%)[^)]*\)", "", question["label"])
            items.append({"key": question["key"], "label": label, "value": shown})
        if items:
            sections.append({"key": section["key"], "title": section["title"], "items": items})
    return sections
