from __future__ import annotations

"""Governed Human Intelligence bridge for production recommendations.

This module converts already-collected person signals into explicit decision
constructs from the approved Success Factors / Next-Best-Question canon. It does
not invent facility lifestyle facts. Missing material evidence remains UNKNOWN.
"""

import base64
import gzip
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PERSON_FIT_PATH = _REPO_ROOT / "database" / "las_vegas_person_fit_summary_v1.b64"
_PERSON_FIT_B64_SHA256 = "387a43e45e316516d55a09a2f45dbca09b4fc683209b0fa4d69d00906885a5fb"
_PERSON_FIT_PAYLOAD_SHA256 = "6fb9207fe46ae421ae0d9c6822a227ecb50eddfc681555dde146cfb9942180e3"
_PERSON_FIT_RECORD_COUNT = 367
_PERSON_FIT_BEDS_KNOWN = 313


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower()


def _nested(payload: Dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _contains_any(value: Any, tokens: Iterable[str]) -> bool:
    text = _norm(value)
    return any(token.lower() in text for token in tokens)


def _explicit_high(value: Any) -> bool:
    return _contains_any(value, ("high", "very important", "important", "strong", "frequent", "daily", "yes", "needed", "need", "often", "helpful"))


def _explicit_low(value: Any) -> bool:
    return _contains_any(value, ("low", "not important", "rare", "minimal", "no", "none", "overwhelming"))


def _explicit_neutral(value: Any) -> bool:
    return _contains_any(value, ("neither", "neutral", "about the same", "no strong preference"))


from app.services.intake_interpretation import (
    _community_size_preference, _recent_bereavement, _social_transition_priority,
    _independence_priority, _transition_participation,
)

def _question(key: str, text: str, reason: str, dimensions: List[str], options: List[str], *, impact: str = "HIGH") -> Dict[str, Any]:
    return {
        "question_key": key,
        "question": text,
        "reason": reason,
        "decision_dimensions": dimensions,
        "information_gain": impact,
        "answer_options": options,
        "policy_reference": "reports/RECOMMENDATION_REQUIRED_DATA_AND_NBQ_V1.md",
    }


def build_human_intelligence_context(questionnaire_state: Dict[str, Any], natural_language_query: str = "", *, intake_facts=None) -> Dict[str, Any]:
    from app.services.intake_interpretation import extract_intake_facts
    facts = intake_facts if intake_facts is not None else extract_intake_facts(questionnaire_state, natural_language_query)
    human = facts["human"]
    community_size = human["community_size_preference"]
    bereavement = human["recent_bereavement"]
    social_transition = human["social_transition_priority"]
    independence = human["independence_priority"]
    transition_participation = human["decision_participation"]

    adaptive_questions: List[Dict[str, Any]] = []
    if social_transition["value"] in {"HIGH", "REVIEW_REQUIRED"} and community_size["value"] == "UNKNOWN":
        adaptive_questions.append(_question(
            "community_size_preference",
            "Would you prefer a small home-like setting with a few residents, a larger senior community with more people and activities, or no preference?",
            "This is used only as an explicit environment preference, not as a claim that facility size predicts quality.",
            ["preference_congruence", "social_transition_fit"],
            ["Small community", "Medium community", "Large community", "No preference"],
        ))
    if bereavement["value"] == "YES" and social_transition["value"] == "REVIEW_REQUIRED":
        adaptive_questions.append(_question(
            "social_interaction_need_after_loss",
            "Since the loss, would more daily social contact feel helpful, overwhelming, or neither?",
            "Bereavement makes transition support relevant but does not tell us how much social contact this person wants.",
            ["social_connection_engagement", "transition_support"],
            ["Helpful", "Overwhelming", "Neither", "Not sure"],
        ))
    if bereavement["value"] == "YES" and transition_participation["value"] == "UNKNOWN":
        adaptive_questions.append(_question(
            "move_participation",
            "How does he feel about the move right now?",
            "Resident participation and move voluntariness are evidence-backed transition factors; the answer changes transition support, not facility desirability by itself.",
            ["decision_participation", "transition_preparation"],
            ["Positive and involved", "Cautious but open", "Reluctant or feels pushed", "Not sure"],
        ))

    transition_support = "STANDARD"
    if transition_participation["value"] == "LOW_PARTICIPATION_RISK":
        transition_support = "HIGH_SUPPORT_REQUIRED"
    elif transition_participation["value"] in {"CAUTIOUS", "ACKNOWLEDGED_UNKNOWN"}:
        transition_support = "ENHANCED_SUPPORT_RECOMMENDED"

    return {
        "version": "human-intelligence-runtime-v2",
        "signals": {
            "recent_bereavement": bereavement,
            "social_transition_priority": social_transition,
            "community_size_preference": community_size,
            "independence_priority": independence,
            "decision_participation": transition_participation,
        },
        "transition_support": {
            "level": transition_support,
            "rank_effect": "NONE_DIRECT",
            "reason": "Decision participation changes transition planning/timing; it is not a provider quality score.",
        },
        "adaptive_questions": adaptive_questions,
        "decision_readiness": "NEEDS_CLARIFICATION" if adaptive_questions else "READY",
        "principles": [
            "Explicit person preferences outrank inference.",
            "Recent bereavement makes transition/social fit decision-relevant but does not determine community style or social intensity.",
            "Facility size is never used as an independent quality factor; only explicit environment preference congruence may use verified capacity.",
            "Missing material person-fit evidence remains UNKNOWN and may trigger clarification.",
            "Questions are asked only for eligibility, ordering, material trade-offs, or transition support.",
        ],
    }


@lru_cache(maxsize=1)
def _person_fit_index() -> Dict[str, Dict[str, Any]]:
    text = _PERSON_FIT_PATH.read_text(encoding="utf-8").strip()
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PERSON_FIT_B64_SHA256:
        raise RuntimeError("Las Vegas person-fit evidence base64 checksum mismatch")
    decoded = gzip.decompress(base64.b64decode(text, validate=True))
    if hashlib.sha256(decoded).hexdigest() != _PERSON_FIT_PAYLOAD_SHA256:
        raise RuntimeError("Las Vegas person-fit evidence payload checksum mismatch")
    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or []
    if payload.get("record_count") != _PERSON_FIT_RECORD_COUNT or len(records) != _PERSON_FIT_RECORD_COUNT:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 367 source records")
    if payload.get("beds_known_count") != _PERSON_FIT_BEDS_KNOWN:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 313 known official bed counts")
    return {str(row.get("canonical_id") or ""): row for row in records if row.get("canonical_id")}


def _community_size_band(beds: Optional[int]) -> str:
    if beds is None:
        return "UNKNOWN"
    if beds <= 10:
        return "MICRO_HOME"
    if beds <= 30:
        return "SMALL_COMMUNITY"
    if beds <= 80:
        return "MEDIUM_COMMUNITY"
    return "LARGE_COMMUNITY"


def _size_fit(preference: str, band: str) -> Optional[float]:
    if preference in {"UNKNOWN", "NO_PREFERENCE"} or band == "UNKNOWN":
        return None
    if preference == "SMALL":
        if band in {"MICRO_HOME", "SMALL_COMMUNITY"}:
            return 100.0
        if band == "MEDIUM_COMMUNITY":
            return 60.0
        return 25.0
    if preference == "MEDIUM":
        if band == "MEDIUM_COMMUNITY":
            return 100.0
        if band in {"SMALL_COMMUNITY", "LARGE_COMMUNITY"}:
            return 65.0
        return 45.0
    if preference == "LARGE":
        if band == "LARGE_COMMUNITY":
            return 100.0
        if band == "MEDIUM_COMMUNITY":
            return 70.0
        if band == "SMALL_COMMUNITY":
            return 45.0
        return 20.0
    return None


def attach_human_person_fit(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> None:
    index = _person_fit_index()
    preference = str((((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")).upper()
    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "")
        evidence = index.get(canonical_id) or {}
        beds = evidence.get("total_bed_count")
        if not isinstance(beds, int):
            beds = None
        band = _community_size_band(beds)
        fit = _size_fit(preference, band)
        row["human_person_fit"] = {
            "community_size": {
                "official_bed_count": beds if beds is not None else "UNKNOWN",
                "community_size_band": band,
                "preference": preference,
                "fit_score": fit if fit is not None else "UNKNOWN",
                "source": "Nevada HCQC / ALiS official detail" if beds is not None else "UNKNOWN",
                "evidence_class": "REGULATORY_VERIFIED" if beds is not None else "UNKNOWN",
                "policy_role": "EXPLICIT_PREFERENCE_CONGRUENCE_ONLY",
                "not_a_quality_factor": True,
            },
            "social_transition_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility social-climate/engagement outcome evidence is attached yet.",
            },
            "independence_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility autonomy/choice evidence is attached yet.",
            },
        }


def person_fit_sort_key(row: Dict[str, Any]) -> tuple[int, float]:
    person_fit = row.get("human_person_fit") if isinstance(row.get("human_person_fit"), dict) else {}
    size = person_fit.get("community_size") if isinstance(person_fit.get("community_size"), dict) else {}
    score = size.get("fit_score")
    if isinstance(score, (int, float)):
        return (0, -float(score))
    return (1, 0.0)


def has_explicit_person_fit_preference(human_context: Dict[str, Any]) -> bool:
    value = str((((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")).upper()
    return value in {"SMALL", "MEDIUM", "LARGE"}
