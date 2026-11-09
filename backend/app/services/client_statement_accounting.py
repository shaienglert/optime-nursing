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
    "FAMILY_RELATION": ("my father", "my mother", "my dad", "my mom", "myself", "אבא", "אמא", "אבי", "אמי"),
    "LOCATION": ("las vegas", "henderson", "summerlin", "לאס וגאס", "הנדרסון"),
    "HOUSEHOLD": ("couple", "married", "husband", "wife", "זוג", "נשוי", "בעל", "אשה", "אישה"),
    "MOBILITY": ("walker", "wheelchair", "walk ", "walking", "meters", "metres", "mobile", "הליכון", "כיסא גלגלים", "כסא גלגלים", "מטר", "נייד"),
    "INDEPENDENCE": ("independent", "independently", "עצמאי", "עצמאית", "עצמאיים"),
    "ADL_SUPPORT": ("bathing", "dressing", "toilet", "transfer", "daily help", "daily assistance", "needs help", "needs assistance", "רחצה", "מקלחת", "לבוש", "להתלבש", "העברה", "עזרה יומית", "סיוע יומי"),
    "MEDICATION": ("medication", "medicine", "תרופות", "תרופה"),
    "DINING": ("food", "dining", "restaurant", "meal", "אוכל", "ארוחות", "מסעד"),
    "ACTIVITIES": ("activities", "classes", "culture", "social", "חוגים", "פעילויות", "תרבות", "חברה"),
    "OUTINGS": ("outings", "trips", "transportation", "טיולים", "הסעות", "יציאות"),
    "OUTDOOR_ENVIRONMENT": ("garden", "gardens", "gardening", "landscap", "grounds", "גינון", "גינה", "גינות", "מטופח"),
    "MEMORY": ("dementia", "memory", "cognitive", "mentally alert", "דמנציה", "זיכרון", "צלול"),
    "MEDICAL_SUPPORT": ("medical", "nursing need", "nursing support", "clinical support"),
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
    protected = re.sub(r"(?<=\d),(?=\d{3}\b)", "<NUM_COMMA>", raw)
    parts = re.split(r"(?:[\n;.!?]+|\s*,\s*|\s+and\s+|\s+but\s+|\s+also\s+|\s+אבל\s+|\s+וגם\s+)", protected, flags=re.IGNORECASE)
    return [part.replace("<NUM_COMMA>", ",").strip(" -–—:\t") for part in parts if part.strip(" -–—:\t")]


def concepts_for_statement(statement: str) -> List[str]:
    value = _norm(statement)
    concepts = [name for name, tokens in KNOWN_CONCEPTS.items() if any(token in value for token in tokens)]
    if re.search(r"\b(?:i am|he is|she is|father is|mother is|dad is|mom is)\s+(?:[5-9]\d|1\d\d)\b", value):
        concepts.append("AGE")
    return list(dict.fromkeys(concepts))


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
        # Legacy ratio describes assigned labels, not semantic comprehension.
        # Preserve the established field for existing consumers, with an
        # explicit meaning and a separate nonfabricated semantic audit status.
        "coverage_percent": 100.0 if not dropped else round(100.0 * (len(rows) - len(dropped)) / max(1, len(rows)), 2),
        "coverage_basis": "STATEMENT_CLASSIFICATION_ONLY",
        "semantic_coverage_percent": None,
        "semantic_coverage_status": "NOT_INDEPENDENTLY_VERIFIED",
        "unresolved_parameters": unresolved,
        "dropped_count": len(dropped),
        "contract": "EVERY_MEANINGFUL_CLIENT_STATEMENT_MUST_BE_USED_ASKED_RESEARCH_REQUIRED_OR_NOT_DECISION_RELEVANT_NEVER_DROPPED",
    }



def reconcile_semantic_statement_coverage(text: str, semantic_packet: Dict[str, Any]) -> Dict[str, Any]:
    """Audit actual source-trace linkage; not an assertion of full comprehension.

    The existing keyword classifier assigns a status to every segment, which
    cannot establish that the interpreter understood it. Reconcile original
    segments with exact source quotes and canonical field materialization.
    Unknown vocabulary is never discarded; unquoted segments remain visible.
    """
    from app.services.canonical_structured_profile import in_schema

    def normalized(value: Any) -> str:
        return " ".join(str(value or "").casefold().split())

    def link_strength(clause: str, quote: str) -> str | None:
        # The canonical splitter removes punctuation and may split at "and".
        # Valid model quotes can also cover only one exact source subspan.
        # Partial overlap is diagnostic, NOT proof the whole clause was used.
        def tokens(value: str) -> list[str]:
            return re.findall(r"\w+", normalized(value), flags=re.UNICODE)

        left, right = tokens(clause), tokens(quote)
        if not left or not right:
            return None
        if len(left) <= len(right):
            full = any(right[i:i+len(left)] == left for i in range(len(right)-len(left)+1))
        else:
            full = False
        if full:
            return "FULL_SOURCE_TRACE"
        # A genuine fragment from the same sentence: at least three consecutive
        # words, or a two-word short clause. Single shared words are not evidence.
        minimum = min(3, len(left), len(right))
        if minimum < 2:
            return None
        for i in range(len(left)-minimum+1):
            part = left[i:i+minimum]
            if any(right[j:j+minimum] == part for j in range(len(right)-minimum+1)):
                return "PARTIAL_SOURCE_TRACE"
        return None

    def at(obj: Any, path: str) -> Any:
        for key in path.split("."):
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
        return obj

    result = account_user_input(text)
    input_text = normalized(text)
    traces = [row for row in semantic_packet.get("statements") or []
              if isinstance(row, dict) and normalized(row.get("raw_text"))
              and normalized(row.get("raw_text")) in input_text]
    patch = semantic_packet.get("questionnaire_patch") or {}
    rows: List[Dict[str, Any]] = []
    for row in result["statements"]:
        clause = normalized(row["statement"])
        linked_with_strength = [
            (trace, strength)
            for trace in traces
            if (strength := link_strength(clause, str(trace.get("raw_text") or "")))
        ]
        linked = [trace for trace, _ in linked_with_strength]
        partially_linked = bool(linked) and not any(
            strength == "FULL_SOURCE_TRACE" for _, strength in linked_with_strength
        )
        paths = sorted({
            str(path) for trace in linked
            for path in (trace.get("mapped_parameters") or [])
            if isinstance(path, str) and in_schema(path)
        })
        materialized = [
            path for path in paths
            if at(patch, path) not in (None, "", [], {})
        ]
        if not linked:
            status = "MISSING_SOURCE_TRACE"
        elif partially_linked:
            status = "PARTIAL_SOURCE_TRACE_REQUIRES_REVIEW"
        elif any(trace.get("status") == "ASKED" for trace in linked):
            status = "CLARIFICATION_TRACE"
        elif any(trace.get("status") == "RESEARCH_REQUIRED" for trace in linked):
            status = "RESEARCH_TRACE"
        elif materialized:
            status = "SOURCE_AND_FIELD_LINKED_NOT_SEMANTICALLY_VERIFIED"
        else:
            status = "TRACED_WITHOUT_MATERIALIZED_FIELD"
        rows.append({
            "index": row["index"], "statement": row["statement"],
            "concepts": row["concepts"], "trace_status": status,
            "mapped_paths": paths, "materialized_paths": materialized,
        })

    traced = sum(row["trace_status"] != "MISSING_SOURCE_TRACE" for row in rows)
    return {
        "statements": rows,
        "statement_count": len(rows),
        "trace_linked_count": traced,
        "missing_source_trace_count": len(rows) - traced,
        "trace_link_rate_percent": round(100.0 * traced / len(rows), 2) if rows else None,
        # Even complete quote coverage is not proof each semantic clause was
        # understood and correctly mapped to the right field.
        "semantic_coverage_percent": None,
        "semantic_coverage_status": "NOT_INDEPENDENTLY_VERIFIED",
        "classification_is_not_interpretation": True,
        "unverified_clauses": [row["statement"] for row in rows
                               if row["trace_status"] in {
                                   "MISSING_SOURCE_TRACE",
                                   "TRACED_WITHOUT_MATERIALIZED_FIELD",
                                   "PARTIAL_SOURCE_TRACE_REQUIRES_REVIEW",
                               }],
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
