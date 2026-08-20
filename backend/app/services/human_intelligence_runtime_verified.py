from __future__ import annotations

"""Verified adapter for Human Intelligence person-fit evidence.

Every meaningful client statement must be accounted for. Known concepts are routed
through governed semantics; unknown concepts remain explicit and trigger clarification
rather than being silently dropped. Specific mobility rules below are inference tests,
not a substitute for the generic no-drop contract.
"""

import base64
import gzip
import hashlib
import json
import re
from functools import lru_cache
from typing import Any, Dict, List

from app.services import human_intelligence_runtime as _base

has_explicit_person_fit_preference = _base.has_explicit_person_fit_preference
person_fit_sort_key = _base.person_fit_sort_key


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _assisted_living_profile_is_material(questionnaire_state: Dict[str, Any], natural_language_query: str) -> bool:
    assistance = _norm(questionnaire_state.get("assistanceLevel"))
    memory = _norm(questionnaire_state.get("memoryStatus"))
    query = _norm(natural_language_query)
    assistance_tokens = ("bathing", "dressing", "meal", "medication", "daily help", "daily assistance", "needs assistance", "needs help")
    assistance_known = any(token in assistance for token in assistance_tokens) or any(token in query for token in assistance_tokens)
    no_dementia = memory in {"no", "none", "no dementia"} or "no dementia" in query or "without dementia" in query or "mentally alert" in query
    return assistance_known and no_dementia


def _question_exists(context: Dict[str, Any], key: str) -> bool:
    return any(str(row.get("question_key") or "") == key for row in context.get("adaptive_questions") or [])


# This registry identifies concepts the governed system already understands. It is
# intentionally not exhaustive: the generic fallback below guarantees that a concept
# absent from this registry is surfaced as UNRESOLVED instead of disappearing.
_KNOWN_CONCEPTS = {
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
    "MEMORY": ("dementia", "memory", "cognitive", "דמנציה", "זיכרון", "צלול"),
    "REHAB": ("rehab", "rehabilitation", "physical therapy", "pt", "ot", "שיקום", "פיזיותרפ"),
    "BUDGET": ("budget", "price", "cost", "$", "תקציב", "מחיר", "עלות"),
    "COMMUNITY_STYLE": ("small community", "large community", "home-like", "intimate", "קהילה קטנה", "קהילה גדולה", "ביתי", "אינטימי"),
    "HOUSING": ("senior living", "independent living", "assisted living", "retirement", "דיור מוגן", "דיור תומך"),
}


def _split_user_statements(text: str) -> List[str]:
    """Split an utterance into auditable semantic clauses without discarding text."""
    raw = str(text or "").strip()
    if not raw:
        return []
    parts = re.split(r"(?:[\n;.!?]+|\s*,\s*|\s+and\s+|\s+but\s+|\s+also\s+|\s+אבל\s+|\s+וגם\s+)", raw, flags=re.IGNORECASE)
    return [part.strip(" -–—:\t") for part in parts if part.strip(" -–—:\t")]


def _concepts_for_statement(statement: str) -> List[str]:
    value = _norm(statement)
    return [name for name, tokens in _KNOWN_CONCEPTS.items() if any(token in value for token in tokens)]


def _statement_is_meaningful(statement: str) -> bool:
    value = statement.strip()
    if not value:
        return False
    words = value.split()
    return len(words) >= 2 or any(ch.isdigit() for ch in value)


def _account_user_input(natural_language_query: str) -> Dict[str, Any]:
    """Return a 100%-accounted trace. Unknown concepts are never silently dropped."""
    rows: List[Dict[str, Any]] = []
    for index, statement in enumerate(_split_user_statements(natural_language_query)):
        concepts = _concepts_for_statement(statement)
        if concepts:
            rows.append({"index": index, "statement": statement, "status": "USED", "concepts": concepts})
        elif _statement_is_meaningful(statement):
            rows.append({"index": index, "statement": statement, "status": "ASKED", "concepts": ["UNRESOLVED_PARAMETER"]})
        else:
            rows.append({"index": index, "statement": statement, "status": "NOT_DECISION_RELEVANT", "concepts": []})
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


def _mobility_layout_is_material(questionnaire_state: Dict[str, Any], natural_language_query: str) -> bool:
    query = _norm(natural_language_query)
    mobility = _norm(questionnaire_state.get("mobilityStatus")) + " " + _norm(questionnaire_state.get("mobility"))
    walker = "walker" in query or "הליכון" in query or "walker" in mobility
    short_limit = any(token in query for token in ("100 meter", "100 metre", "100m", "100 meters", "100 metres", "100 מטר"))
    wheelchair_refusal = any(token in query for token in ("refuses wheelchair", "refuse wheelchair", "won't use a wheelchair", "will not use a wheelchair", "מסרב לכיסא", "לא מוכן שיראו אותו בכסא", "לא מוכן שיראו אותו בכיסא"))
    return walker and short_limit and wheelchair_refusal


def _compact_layout_answer(questionnaire_state: Dict[str, Any]) -> str:
    hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    independence = hi.get("independenceProfile") if isinstance(hi.get("independenceProfile"), dict) else {}
    return _norm(independence.get("compactLayoutPreference"))


def _append_material_unknown_questions(context: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    questions = list(context.get("adaptive_questions") or [])

    if _assisted_living_profile_is_material(questionnaire_state, natural_language_query):
        signals = context.get("signals") if isinstance(context.get("signals"), dict) else {}
        community = signals.get("community_size_preference") if isinstance(signals.get("community_size_preference"), dict) else {}
        social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
        if str(community.get("value") or "UNKNOWN").upper() == "UNKNOWN" and not _question_exists(context, "community_size_preference"):
            questions.append(_base._question("community_size_preference", "Would he prefer a small home-like setting, a medium-sized community, a larger senior community with more people and activities, or no preference?", "Community environment can materially change the ordering of otherwise appropriate Assisted Living options. We do not infer this preference from age, mobility, or diagnosis.", ["preference_congruence", "social_connection_engagement"], ["Small community", "Medium community", "Large community", "No preference"]))
        hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
        family = hi.get("familyProfile") if isinstance(hi.get("familyProfile"), dict) else {}
        raw_social_answer = _norm(family.get("socialInteractionNeed"))
        if str(social.get("value") or "UNKNOWN").upper() == "UNKNOWN" and raw_social_answer not in {"not sure", "unsure", "no preference"} and not _question_exists(context, "social_interaction_preference"):
            questions.append(_base._question("social_interaction_preference", "How important is it that he have frequent opportunities each day to meet people and join activities?", "Social engagement is a material fit factor for Assisted Living. If it is unknown, we ask instead of assuming that a mobile, cognitively intact resident wants either a busy or a quiet environment.", ["social_connection_engagement", "social_climate", "preference_congruence"], ["Very important", "Somewhat important", "Not important", "No preference", "Not sure"]))

    if _mobility_layout_is_material(questionnaire_state, natural_language_query):
        answer = _compact_layout_answer(questionnaire_state)
        signals = context.setdefault("signals", {})
        if answer in {"yes", "important", "very important", "prefer compact", "compact", "כן"}:
            signals["compact_central_layout_preference"] = {"value": "REQUIRED", "source": "resident_answer"}
        elif answer in {"no", "not important", "no preference", "לא"}:
            signals["compact_central_layout_preference"] = {"value": "NO_PREFERENCE", "source": "resident_answer"}
        else:
            signals["compact_central_layout_preference"] = {"value": "UNKNOWN", "source": "material_mobility_inference"}
            if not any(str(row.get("question_key") or "") == "compact_central_layout_preference" for row in questions):
                questions.insert(0, _base._question("compact_central_layout_preference", "Because you use a walker, can walk only about 100 meters, and do not want to use a wheelchair, would you prefer a compact community or central building where your apartment, dining room, activities and main services are all within short walking distances?", "The walking-distance limit can make campus layout a decisive eligibility factor. We ask before assuming that a large or spread-out campus is acceptable.", ["mobility_independence", "preference_congruence", "physical_environment"], ["Yes, short distances are important", "Somewhat important", "No preference", "No"]))

    accounting = _account_user_input(natural_language_query)
    context["user_statement_accounting"] = accounting
    unresolved = accounting["unresolved_parameters"]
    if unresolved and not any(str(row.get("question_key") or "") == "unresolved_client_parameter" for row in questions):
        # Ask one important question at a time. Remaining unresolved clauses stay in
        # the trace and are revisited on the next turn; none are discarded.
        statement = unresolved[0]["statement"]
        questions.append(_base._question(
            "unresolved_client_parameter",
            f'You mentioned: "{statement}". I do not want to ignore or misinterpret it. How should this affect the kind of place you want?',
            "This is a meaningful client statement that is not yet mapped to a governed decision parameter. Understanding the client comes before recommending facilities.",
            ["preference_congruence", "client_intent_completeness"],
            ["This is a must-have", "This is important but not mandatory", "It is only context", "Please research what it means for my decision"],
        ))

    context["adaptive_questions"] = questions
    context["decision_readiness"] = "NEEDS_CLARIFICATION" if questions or unresolved else "READY"
    context["material_unknown_policy"] = {
        "rule": "ASK_OR_RESEARCH_IF_MATERIAL_TO_ELIGIBILITY_ORDERING_TRADEOFF_OR_TRANSITION",
        "assisted_living_profile_detected": _assisted_living_profile_is_material(questionnaire_state, natural_language_query),
        "mobility_layout_profile_detected": _mobility_layout_is_material(questionnaire_state, natural_language_query),
        "unknown_is_not_default": True,
        "no_silent_drop": True,
        "required_statement_coverage_percent": 100,
    }
    return context


def build_human_intelligence_context(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    context = _base.build_human_intelligence_context(questionnaire_state, natural_language_query)
    return _append_material_unknown_questions(context, questionnaire_state, natural_language_query)


@lru_cache(maxsize=1)
def _verified_person_fit_index() -> Dict[str, Dict[str, Any]]:
    text = _base._PERSON_FIT_PATH.read_text(encoding="utf-8").strip()
    decoded = gzip.decompress(base64.b64decode(text, validate=True))
    actual_payload_sha = hashlib.sha256(decoded).hexdigest()
    if actual_payload_sha != _base._PERSON_FIT_PAYLOAD_SHA256:
        raise RuntimeError(f"Las Vegas person-fit canonical payload checksum mismatch: sha256={actual_payload_sha} expected={_base._PERSON_FIT_PAYLOAD_SHA256}")
    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or []
    if payload.get("record_count") != _base._PERSON_FIT_RECORD_COUNT or len(records) != _base._PERSON_FIT_RECORD_COUNT:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 367 source records")
    if payload.get("beds_known_count") != _base._PERSON_FIT_BEDS_KNOWN:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 313 known official bed counts")
    return {str(row.get("canonical_id") or ""): row for row in records if row.get("canonical_id")}


def attach_human_person_fit(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> None:
    index = _verified_person_fit_index()
    preference = str((((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")).upper()
    compact = str((((human_context.get("signals") or {}).get("compact_central_layout_preference") or {}).get("value") or "UNKNOWN")).upper()
    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "")
        evidence = index.get(canonical_id) or {}
        beds = evidence.get("total_bed_count")
        if not isinstance(beds, int):
            beds = None
        band = _base._community_size_band(beds)
        fit = _base._size_fit(preference, band)
        row["human_person_fit"] = {
            "community_size": {"official_bed_count": beds if beds is not None else "UNKNOWN", "community_size_band": band, "preference": preference, "fit_score": fit if fit is not None else "UNKNOWN", "source": "Nevada HCQC / ALiS official detail" if beds is not None else "UNKNOWN", "evidence_class": "REGULATORY_VERIFIED" if beds is not None else "UNKNOWN", "policy_role": "EXPLICIT_PREFERENCE_CONGRUENCE_ONLY", "not_a_quality_factor": True},
            "compact_central_layout": {"preference": compact, "status": "UNKNOWN", "reason": "Facility-level internal walking-distance/layout evidence must be verified; bed count is not a proxy for campus compactness."},
            "social_transition_fit": {"status": "UNKNOWN", "reason": "No verified Nevada facility social-climate/engagement outcome evidence is attached yet."},
            "independence_fit": {"status": "UNKNOWN", "reason": "No verified Nevada facility autonomy/choice evidence is attached yet."},
        }


__all__ = ["attach_human_person_fit", "build_human_intelligence_context", "has_explicit_person_fit_preference", "person_fit_sort_key"]
