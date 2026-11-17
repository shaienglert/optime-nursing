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

import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

KEY_HE: Dict[str, str] = {
    "LICENSE_CURRENTLY_VALID": "רישיון בתוקף",
    "IL_FUNCTIONAL_LEVEL": "מקבל את רמת התפקוד",
    "IL_MOH_CODE_AGREEMENT": "הסכם קוד עם משרד הבריאות",
    "IL_FUNDING_TRACK": "מקבל את מסלול המימון",
    "IL_ACCEPTS_VENTILATED": "מקבל מונשמים",
    "IL_WANDERING_SAFE": "מחלקה סגורה או השגחה למשוטטים",
    "IL_ACCEPTS_PEG": "מקבל הזנה ב־PEG",
    "IL_ACCEPTS_NG_TUBE": "מקבל זונדה",
    "IL_ACCEPTS_COUPLE": "מקבל זוגות",
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

def label(key: str) -> str:
    base = str(key).split(":", 1)[0]
    return KEY_HE.get(base, base)


def _interpreter_configured() -> bool:
    return bool(os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip() and os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip())


def interpret(questionnaire_state: Dict[str, Any], text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Buttons + family text -> decision questionnaire, through the shared interpreter."""
    text = (text or "").strip()
    if not text:
        return questionnaire_state, {"status": "NO_TEXT"}
    if not _interpreter_configured():
        return questionnaire_state, {
            "status": "UNPROCESSED",
            "message": "את מה שכתבתם במלל חופשי לא הצלחנו לעבד כרגע, ולכן הוא לא השפיע על התוצאות. התוצאות מבוססות על התשובות בשאלון.",
        }
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
    from app.services.semantic_intent_ai import interpret_client_intent_with_ai

    try:
        result = interpret_client_intent_with_ai(user_text=text, questionnaire_state=questionnaire_state)
    except Exception:  # the interpreter must never block the family
        return questionnaire_state, {
            "status": "UNPROCESSED",
            "message": "את מה שכתבתם במלל חופשי לא הצלחנו לעבד כרגע, ולכן הוא לא השפיע על התוצאות. התוצאות מבוססות על התשובות בשאלון.",
        }
    profile = build_structured_profile(questionnaire_state, result, family_text=text)
    state = materialize_questionnaire(profile)
    for key, value in questionnaire_state.items():
        if key != "israelMarket":
            state.setdefault(key, value)
    return state, {
        "status": "INTERPRETED",
        "conflicts": profile.get("conflicts") or [],
        "unprocessed": profile.get("unprocessed") or [],
        "clarification_question": result.get("next_question"),
    }


def missing_required(israel: Dict[str, Any]) -> List[str]:
    level = str(israel.get("functionalLevel") or "").strip()
    missing = []
    if not level:
        missing.append("functionalLevel")
    if level.upper() != "COMPLEX_NURSING" and not str(israel.get("fundingPathway") or "").strip():
        missing.append("fundingPathway")
    if not str(israel.get("city") or "").strip():
        missing.append("city")
    return missing


def _card(record: Dict[str, Any], fit: Dict[str, Any], registration: Optional[Dict[str, Any]], rank: int) -> Dict[str, Any]:
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
        "musts_met": [{"key": k, "label": label(k)} for k in fit.get("must_pass") or []],
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
    from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
    from app.services.israel_facility_import import load_israel_records
    from app.services.israel_facility_registration import load_israel_registration
    from app.services.oomniker_optimizer import analyze_oomniker

    text = natural_language_query or str(questionnaire_state.get("notes") or "")
    state, interpretation = interpret(questionnaire_state, text)
    israel = state.get("israelMarket") if isinstance(state.get("israelMarket"), dict) else {}
    missing = missing_required(israel)
    if missing:
        return {"status": "NEEDS_INPUT", "missing": missing, "interpretation": interpretation, "results": []}

    intent = build_client_intent({"israelMarket": israel}, text, {}, {})
    records, generated_at = load_israel_records()
    evaluated = [(record, evaluate_candidate_intent(record, intent)) for record in records]

    # MUSTs the family left open; their unknowns belong to the family, not the facilities.
    family_unknown = ["IL_FUNCTIONAL_LEVEL"] if str(israel.get("functionalLevel") or "").upper() == "UNCLEAR" else []
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
    cards = [_card(record, fit, load_israel_registration(db, record["canonical_id"]), rank) for rank, (record, fit) in enumerate(shown, 1)]

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
        "musts": [{"key": m["key"], "label": label(m["key"])} for m in intent.get("must_haves") or []],
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
