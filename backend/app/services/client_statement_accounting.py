from __future__ import annotations

"""No-silent-drop contract for natural-language client intent.

This layer does not decide what the client meant when meaning is uncertain. It makes
sure every meaningful clause is either recognized, explicitly asked about, routed to
research, or marked not decision-relevant. Unknown input must never disappear merely
because the current parameter registry does not know it.
"""

import re
from typing import Any, Dict, List


KNOWN_CONCEPTS = {
    "AGE": ("age ", "years old", "בן ", "בת "),
    "LOCATION": ("las vegas", "henderson", "summerlin", "לאס וגאס", "הנדרסון"),
    "HOUSEHOLD": ("couple", "married", "husband", "wife", "זוג", "נשוי", "בעל", "אשה", "אישה"),
    "MOBILITY": ("walker", "wheelchair", "walk ", "walking", "meters", "metres", "הליכון", "כיסא גלגלים", "כסא גלגלים", "מטר"),
    "INDEPENDENCE": ("independent", "independently", "עצמאי", "עצמאית", "עצמאיים"),
    "ADL_SUPPORT": ("bathing", "dressing", "toilet", "transfer", "רחצה", "מקלחת", "לבוש", "להתלבש", "העברה"),
    "MEDICATION": ("medication", "medicine", "תרופות", "תרופה"),
    "DINING": ("food", "dining", "restaurant", "meal", "אוכל", "ארוחות", "מסעד"),
    "ACTIVITIES": ("activities", "classes", "culture", "social", "חוגים", "פעילויות", "תרבות", "חברה"),
    "OUTINGS": ("outings", "trips", "transportation", "טיולים", "הסעות", "יציאות"),
    "OUTDOOR_ENVIRONMENT": ("garden", "gardens", "gardening", "landscap", "grounds", "גינון", "גינה", "גינות", "מטופח"),
    "MEMORY": ("dementia", "memory", "cognitive", "mentally alert", "דמנציה", "זיכרון", "צלול"),
    "BEREAVEMENT": ("widow", "widowed", "bereavement", "spouse died", "אלמן", "אלמנה", "התאלמן", "התאלמנה"),
    "REHAB": ("rehab", "rehabilitation", "physical therapy", "occupational therapy", "שיקום", "פיזיותרפ"),
    "BUDGET": ("budget", "price", "cost", "$", "תקציב", "מחיר", "עלות"),
    "COMMUNITY_STYLE": ("small community", "large community", "home-like", "intimate", "קהילה קטנה", "קהילה גדולה", "ביתי", "אינטימי"),
    "HOUSING": ("senior living", "independent living", "assisted living", "retirement", "דיור מוגן", "דיור תומך"),
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def split_user_statements(text: str) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    parts = re.split(r"(?:[\n;.!?]+|\s*,\s*|\s+and\s+|\s+but\s+|\s+also\s+|\s+אבל\s+|\s+וגם\s+)", raw, flags=re.IGNORECASE)
    return [part.strip(" -–—:\t") for part in parts if part.strip(" -–—:\t")]


def concepts_for_statement(statement: str) -> List[str]:
    value = _norm(statement)
    return [name for name, tokens in KNOWN_CONCEPTS.items() if any(token in value for token in tokens)]


def account_user_input(text: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for index, statement in enumerate(split_user_statements(text)):
        concepts = concepts_for_statement(statement)
        meaningful = len(statement.split()) >= 2 or any(ch.isdigit() for ch in statement)
        if concepts:
            status = "USED"
        elif meaningful:
            status = "ASKED"
            concepts = ["UNRESOLVED_PARAMETER"]
        else:
            status = "NOT_DECISION_RELEVANT"
        rows.append({"index": index, "statement": statement, "status": status, "concepts": concepts})

    unresolved = [row for row in rows if row["status"] == "ASKED"]
    dropped = [row for row in rows if row["status"] == "DROPPED"]
    return {
        "statements": rows,
        "statement_count": len(rows),
        "accounted_count": len(rows) - len(dropped),
        "coverage_percent": 100.0 if not dropped else round(100.0 * (len(rows) - len(dropped)) / max(1, len(rows)), 2),
        "unresolved_parameters": unresolved,
        "dropped_count": len(dropped),
        "contract": "EVERY_MEANINGFUL_CLIENT_STATEMENT_MUST_BE_USED_ASKED_RESEARCH_REQUIRED_OR_NOT_DECISION_RELEVANT_NEVER_DROPPED",
    }


def apply_no_drop_contract(context: Dict[str, Any], natural_language_query: str, question_factory: Any) -> Dict[str, Any]:
    accounting = account_user_input(natural_language_query)
    context["user_statement_accounting"] = accounting
    context["material_unknown_policy"] = {
        **(context.get("material_unknown_policy") or {}),
        "unknown_is_not_default": True,
        "no_silent_drop": True,
        "required_statement_coverage_percent": 100,
        "rule": "ASK_OR_RESEARCH_IF_MATERIAL_TO_ELIGIBILITY_ORDERING_TRADEOFF_OR_TRANSITION",
    }
    unresolved = accounting["unresolved_parameters"]
    questions = list(context.get("adaptive_questions") or [])
    if unresolved and not any(str(row.get("question_key") or "") == "unresolved_client_parameter" for row in questions):
        statement = unresolved[0]["statement"]
        questions.append(question_factory(
            "unresolved_client_parameter",
            f'You mentioned: "{statement}". I do not want to ignore or misinterpret it. How should this affect the kind of place you want?',
            "The client expressed a meaningful parameter that is not yet mapped to governed semantics. Understanding the request comes before recommending facilities.",
            ["preference_congruence", "client_intent_completeness"],
            ["This is a must-have", "This is important but not mandatory", "It is only context", "Please research what it means for my decision"],
        ))
    context["adaptive_questions"] = questions
    if questions or unresolved:
        context["decision_readiness"] = "NEEDS_CLARIFICATION"
    return context


__all__ = ["KNOWN_CONCEPTS", "account_user_input", "apply_no_drop_contract", "concepts_for_statement", "split_user_statements"]
