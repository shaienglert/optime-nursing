"""10 Israeli seekers, each run twice against the 450 synthetic facilities:
once through the structured Hebrew questionnaire and once as free text.

The free-text run goes through the shared AI interpreter when it is configured
(OPTIME_SEMANTIC_AI_URL / _MODEL / _API_KEY): its Israeli fields are merged into the
questionnaire state exactly as the live intake does. Without the interpreter, the
text reaches the engine as a plain query, which is what a deployment without the
interpreter would do.

For each seeker the report compares:
- what the engine understood (MUST conditions and ranking preferences, with values);
- what it did (pass / pending / fail counts, top-5 overlap).

Usage: python scripts/compare_israel_structured_vs_freetext.py [--out reports/israel_structured_vs_freetext.md]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["OPTIME_CANONICAL_MARKET"] = "israel-synthetic"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/oomnik_il_compare.db")

from app.database import Base, engine  # noqa: E402
import app.models.facility  # noqa: E402,F401
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key  # noqa: E402
from app.services.israel_facility_registration import apply_registration  # noqa: E402

DATA = ROOT / "database" / "israel_synthetic"

SEEKERS = [
    {
        "title": "אמא סיעודית בחיפה, קוד, דוברת רוסית",
        "structured": {"relationship": "אמא", "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "חיפה",
                       "maxDistanceKm": 20, "language": "RU", "community": "TRADITIONAL", "kashrut": "KOSHER"},
        "text": "אני מחפשת מקום לאמא שלי, היא סיעודית לגמרי. יש לנו קוד של משרד הבריאות. אנחנו גרים בחיפה ולא רוצים יותר מ-20 ק\"מ. "
                "אמא מדברת בעיקר רוסית, אנחנו משפחה מסורתית ואוכל כשר חשוב לנו.",
    },
    {
        "title": "אבא תשוש נפש משוטט, חרדי, ירושלים, פרטי",
        "structured": {"relationship": "אבא", "functionalLevel": "COGNITIVE_FRAIL", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 16000,
                       "city": "ירושלים", "maxDistanceKm": 20, "medicalNeeds": ["WANDERING"],
                       "community": "HAREDI", "kashrut": "MEHADRIN", "shabbat": "IMPORTANT", "sameGenderCare": "IMPORTANT"},
        "text": "אבא שלי בן 84 עם דמנציה מתקדמת, הוא יוצא מהבית ומסתובב ברחובות ולכן צריך מחלקה סגורה. אנחנו חרדים, צריך כשרות מהדרין "
                "ושמירת שבת, וחשוב שרק גבר ירחץ וילביש אותו. נשלם באופן פרטי עד 16 אלף בחודש, באזור ירושלים.",
    },
    {
        "title": "זוג: היא עצמאית, הוא סיעודי, רעננה",
        "structured": {"relationship": "הורים", "functionalLevel": "NURSING", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 20000,
                       "city": "רעננה", "maxDistanceKm": 40, "isCouple": True, "partnerSameLevel": False},
        "text": "ההורים שלי רוצים לעבור יחד. אמא עצמאית לגמרי ואבא סיעודי אחרי שבץ. אנחנו מרעננה, אפשר עד 40 ק\"מ. "
                "התקציב שלהם עד 20,000 ש\"ח לחודש, מימון פרטי.",
    },
    {
        "title": "מונשם, קוד, תל אביב",
        "structured": {"relationship": "אבא", "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "תל אביב - יפו",
                       "medicalNeeds": ["VENTILATION"]},
        "text": "אבא שלי מונשם מאז האשפוז, יש לו קוד משרד הבריאות. אנחנו בתל אביב אבל מוכנים לכל מקום בארץ שמקבל מונשמים.",
    },
    {
        "title": "אישה עצמאית לדיור מוגן, הרצליה, ממ\"ד בקומה",
        "structured": {"relationship": "עבורי", "functionalLevel": "INDEPENDENT", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 9000,
                       "depositCapIls": 1500000, "city": "הרצליה", "maxDistanceKm": 10, "community": "SECULAR", "shelterNeed": "FLOOR"},
        "text": "אני בת 76, עצמאית, ומחפשת דיור מוגן ליד הרצליה, עד 10 ק\"מ. יכולה להפקיד עד מיליון וחצי ולשלם עד 9,000 בחודש. "
                "אני חילונית. חשוב לי שיהיה מרחב מוגן באותה קומה.",
    },
    {
        "title": "אבא דרוזי סיעודי עם PEG, קוד, דלית אל-כרמל",
        "structured": {"relationship": "אבא", "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "דלית אל-כרמל",
                       "maxDistanceKm": 40, "medicalNeeds": ["PEG"], "language": "AR", "community": "DRUZE"},
        "text": "אבא שלי מדלית אל-כרמל, סיעודי ומוזן דרך PEG. יש קוד של משרד הבריאות. הוא מדבר ערבית, ואנחנו דרוזים. עד 40 ק\"מ מהבית.",
    },
    {
        "title": "אמא מוסלמית תשושה, רווחה, נצרת",
        "structured": {"relationship": "אמא", "functionalLevel": "FRAIL", "fundingPathway": "WELFARE_ASSISTANCE", "city": "נצרת",
                       "maxDistanceKm": 20, "language": "AR", "community": "MUSLIM", "sameGenderCare": "IMPORTANT"},
        "text": "אמא שלי תשושה, צריכה עזרה במקלחת ובלבוש אבל הולכת לבד. המימון דרך הרווחה. אנחנו מנצרת, עד 20 ק\"מ, מוסלמים ודוברי ערבית. "
                "חשוב לנו שאישה תעזור לה במקלחת.",
    },
    {
        "title": "אמא סיעודית בנהריה, תנאי: ממ\"ד בחדר",
        "structured": {"relationship": "אמא", "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "נהריה", "maxDistanceKm": 40,
                       "shelterNeed": "ROOM", "shelterIsCondition": True},
        "text": "אמא סיעודית, יש קוד. אנחנו בנהריה, עד 40 ק\"מ. אחרי השנה האחרונה אני לא מוכנה לשום מקום בלי ממ\"ד בתוך החדר, זה תנאי.",
    },
    {
        "title": "אבא סיעודי מרותק למיטה, פרטי, פתח תקווה",
        "structured": {"relationship": "אבא", "functionalLevel": "NURSING", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 15000,
                       "city": "פתח תקווה", "maxDistanceKm": 25, "bedridden": True},
        "text": "אבא מרותק למיטה, סיעודי. נשלם פרטי עד 15 אלף. אנחנו בפתח תקווה, עד 25 ק\"מ. חשוב שיהיה פתרון מוגן גם למי שבמיטה.",
    },
    {
        "title": "סבתא, מצב לא ברור, באר שבע",
        "structured": {"relationship": "סבתא", "functionalLevel": "UNCLEAR", "fundingPathway": "UNCLEAR", "city": "באר שבע"},
        "text": "סבתא שלי מבאר שבע התחילה לשכוח דברים ונפלה פעמיים. אנחנו עוד לא יודעים אם היא תשושה או סיעודית ולא בדקנו מימון.",
    },
]

GATE_HE = {
    "LICENSE_CURRENTLY_VALID": "רישיון בתוקף", "IL_FUNCTIONAL_LEVEL": "רמת תפקוד", "IL_MOH_CODE_AGREEMENT": "הסכם קוד",
    "IL_FUNDING_TRACK": "מסלול מימון", "IL_ACCEPTS_VENTILATED": "מונשמים", "IL_WANDERING_SAFE": "משוטטים",
    "IL_ACCEPTS_PEG": "PEG", "IL_ACCEPTS_NG_TUBE": "זונדה", "IL_ACCEPTS_COUPLE": "זוגות",
    "IL_SHELTER_MINIMUM": "מיגון (תנאי)", "IL_BEDRIDDEN_SHELTER": "מיגון למרותקים", "IL_COMMUNITY": "ציבור",
    "IL_KASHRUT": "כשרות", "IL_SHABBAT": "שבת", "IL_SAME_GENDER_CARE": "טיפול מאותו מגדר", "IL_LANGUAGE": "שפה", "IL_SHELTER": "מיגון (העדפה)", "IL_BUDGET": "תקציב",
    "IL_AVAILABILITY": "זמינות", "IL_DISTANCE": "טווח מרחק", "IL_PROXIMITY": "קרבה",
}


def _value(item):
    value = item.get("value")
    if isinstance(value, dict):
        return value.get("max_km") or ""
    if isinstance(value, list):
        return "+".join(value)
    return "" if value is None else value


def interpreter_configured() -> bool:
    return bool(os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip() and os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip())


def free_text_state(text):
    """(questionnaire state, interpreter status, clarification question or None)."""
    if not interpreter_configured():
        return {"notes": text}, "NOT_CONFIGURED", None
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
    from app.services.semantic_intent_ai import interpret_client_intent_with_ai

    try:
        result = interpret_client_intent_with_ai(user_text=text, questionnaire_state={})
    except RuntimeError as error:
        return {"notes": text}, f"ERROR:{str(error)[:80]}", None
    state = materialize_questionnaire(build_structured_profile({}, result, family_text=text))
    state["notes"] = text
    return state, str(result.get("decision_readiness")), result.get("next_question")


def understood(intent):
    musts = {m["key"]: _value(m) for m in intent["must_haves"]}
    nice = {n["key"]: _value(n) for n in intent["nice_to_haves"] if str(n["key"]).startswith("IL_")}
    other_nice = [n["key"] for n in intent["nice_to_haves"] if not str(n["key"]).startswith("IL_")]
    return musts, nice, other_nice


def run(rows, intent):
    fits = [(row, evaluate_candidate_intent(row, intent)) for row in rows]
    gates = Counter(fit["hard_gate"] for _, fit in fits)
    passing = sorted((f for f in fits if f[1]["hard_gate"] == "PASS"), key=lambda f: intent_rank_key({"client_intent_fit": f[1]}))
    shown = sorted((f for f in fits if f[1]["hard_gate"] != "FAIL"), key=lambda f: intent_rank_key({"client_intent_fit": f[1]}))
    failed = [r["canonical_id"] for r, f in fits if f["hard_gate"] == "FAIL"]
    return gates, [r["canonical_id"] for r, _ in passing], [r["canonical_id"] for r, _ in shown], failed


SHELTER_RANK = {"ROOM": 0, "FLOOR": 1, "BUILDING": 2, "NEARBY": 3}


def violations(fam, registration):
    """Independent re-check, written apart from the engine: which of the family's stated
    conditions does a facility the engine passed actually break?"""
    if registration is None:
        return ["לא רשום"]
    q = registration["questionnaire"]
    bad = []
    if fam.get("functionalLevel") in {"INDEPENDENT", "FRAIL", "NURSING", "COGNITIVE_FRAIL"} and fam["functionalLevel"] not in registration["functional_levels_served"]:
        bad.append("רמת תפקוד")
    if fam.get("fundingPathway") == "MOH_CODE" and registration["moh_code_agreement"] != "YES":
        bad.append("הסכם קוד")
    track = {"PRIVATE": "PRIVATE", "WELFARE_ASSISTANCE": "WELFARE"}.get(fam.get("fundingPathway"))
    if track and track not in q.get("payment_tracks", []):
        bad.append("מסלול מימון")
    for need, key in (("VENTILATION", "accepts_ventilated"), ("WANDERING", "wandering_safe"), ("PEG", "accepts_peg"), ("NG_TUBE", "accepts_ng_tube")):
        if need in fam.get("medicalNeeds", []) and q.get(key) != "YES":
            bad.append(need)
    if fam.get("isCouple"):
        policy = q.get("couples")
        if policy == "NO" or policy is None or (policy == "SAME_LEVEL" and not fam.get("partnerSameLevel")):
            bad.append("זוגות")
    if fam.get("shelterIsCondition") and SHELTER_RANK.get(q.get("shelter"), 9) > SHELTER_RANK[fam["shelterNeed"]]:
        bad.append("מיגון")
    if fam.get("bedridden") and q.get("shelter_bedridden") not in {"PROTECTED_IN_ROOM", "MOVED_IN_BED"}:
        bad.append("מרותקים")
    if registration["license_expiration_date"] < "2026-11-15":
        bad.append("רישיון")
    return bad


def fmt(d):
    return ", ".join(f"{GATE_HE.get(k, k)}{'=' + str(v) if v not in ('', None) else ''}" for k, v in d.items()) or "-"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "reports" / "israel_structured_vs_freetext.md"))
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    records = json.loads((DATA / "facility_universe.json").read_text(encoding="utf-8"))["records"]
    registrations = json.loads((DATA / "registrations.json").read_text(encoding="utf-8"))["registrations"]
    rows = [apply_registration(r, registrations.get(r["canonical_id"])) for r in records]

    summary = []
    detail = []
    for seeker in SEEKERS:
        s_intent = build_client_intent({"israelMarket": seeker["structured"]}, "", {}, {})
        f_state, interpreter_status, question = free_text_state(seeker["text"])
        f_intent = build_client_intent(f_state, seeker["text"], {}, {})
        s_m, s_n, _ = understood(s_intent)
        f_m, f_n, f_other = understood(f_intent)
        s_g, s_pass, s_shown, s_failed = run(rows, s_intent)
        wrongly_excluded = [cid for cid in s_failed if registrations.get(cid) and not violations(seeker["structured"], registrations[cid])]
        broken = Counter(v for cid in s_pass for v in violations(seeker["structured"], registrations.get(cid)))
        f_g, f_pass, f_shown, _ = run(rows, f_intent)
        missed_m = [k for k in s_m if k not in f_m]
        missed_n = [k for k in s_n if k not in f_n]
        overlap = len(set(s_shown[:5]) & set(f_shown[:5]))
        summary.append(
            f"| {seeker['title']} | {len(s_m)} / {len(s_n)} | {len(f_m)} / {len(f_n)} | "
            f"{s_g.get('PASS', 0)} | {sum(broken.values())} | {f_g.get('PASS', 0)} | {f_g.get('PENDING_VERIFICATION', 0)} | {overlap}/5 |"
        )
        detail += [
            f"### {seeker['title']}",
            "",
            f"**מלל חופשי:** {seeker['text']}",
            "",
            f"- **מפענח AI:** {interpreter_status}" + (f" — שאלת הבהרה: {question}" if question else ""),
            f"- **שאלון, תנאי חובה:** {fmt(s_m)}",
            f"- **שאלון, העדפות:** {fmt(s_n)}",
            f"- **מלל חופשי, תנאי חובה:** {fmt(f_m)}",
            f"- **מלל חופשי, העדפות:** {fmt(f_n)}" + (f" (ועוד מפתחות של השוק האמריקאי: {', '.join(f_other)})" if f_other else ""),
            f"- **לא הובן מהמלל:** {', '.join(GATE_HE.get(k, k) for k in missed_m + missed_n) or 'הכול הובן'}",
            f"- **תוצאה בשאלון:** {s_g.get('PASS', 0)} מתאימים, {s_g.get('PENDING_VERIFICATION', 0)} חסר מידע, {s_g.get('FAIL', 0)} נפסלים",
            f"- **תוצאה במלל:** {f_g.get('PASS', 0)} מתאימים, {f_g.get('PENDING_VERIFICATION', 0)} חסר מידע, {f_g.get('FAIL', 0)} נפסלים",
            f"- **חפיפה בחמשת הראשונים שמוצגים:** {overlap} מתוך 5",
            f"- **בדיקה בלתי תלויה של {len(s_pass)} המתאימים בשאלון:** "
            + (", ".join(f"{k} ({n})" for k, n in broken.items()) if broken else "אף מוסד לא מפר תנאי של המשפחה")
            + f"; מוסדות שנפסלו למרות שעומדים בכל התנאים: {len(wrongly_excluded)}",
            "",
        ]

    lines = [
        "# שאלון מול מלל חופשי: 10 מחפשים, 450 מוסדות סינתטיים",
        "",
        f"מפענח המלל החופשי (AI): {'מחובר' if interpreter_configured() else 'לא מחובר בסביבת ההרצה הזו, ולכן המלל מגיע למנוע בלי פענוח'}.",
        "",
        "| מחפש | שאלון: חובה / העדפות | מלל: חובה / העדפות | מתאימים (שאלון) | הפרות בבדיקה בלתי תלויה | מתאימים (מלל) | חסר מידע (מלל) | חפיפה ב-5 הראשונים |",
        "|---|---|---|---|---|---|---|---|",
        *summary,
        "",
        "(בכל ספירת \"חובה\" נכלל גם \"רישיון בתוקף\", שמתווסף תמיד.)",
        "",
        *detail,
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
