from __future__ import annotations

"""Verified adapter for Human Intelligence person-fit evidence.

The canonical integrity boundary is the decoded JSON payload, not the gzip/base64
transport wrapper. The wrapper can change without changing the evidence. This
adapter keeps the payload SHA-256 and record-count invariants hard, while reusing
the Human Intelligence signal semantics from ``human_intelligence_runtime``.

This adapter also closes a production decision gap: when a resident fact is
material to ordering and is still UNKNOWN, the system must ask rather than silently
continue with a default ranking. UNKNOWN remains UNKNOWN until the person answers.
"""

import base64
import gzip
import hashlib
import json
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

    assistance_tokens = (
        "bathing",
        "dressing",
        "meal",
        "medication",
        "daily help",
        "daily assistance",
        "needs assistance",
        "needs help",
    )
    assistance_known = any(token in assistance for token in assistance_tokens) or any(
        token in query for token in assistance_tokens
    )
    no_dementia = (
        memory in {"no", "none", "no dementia"}
        or "no dementia" in query
        or "without dementia" in query
        or "mentally alert" in query
    )
    return assistance_known and no_dementia


def _question_exists(context: Dict[str, Any], key: str) -> bool:
    return any(str(row.get("question_key") or "") == key for row in context.get("adaptive_questions") or [])


def _append_material_unknown_questions(
    context: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
) -> Dict[str, Any]:
    if not _assisted_living_profile_is_material(questionnaire_state, natural_language_query):
        return context

    signals = context.get("signals") if isinstance(context.get("signals"), dict) else {}
    community = signals.get("community_size_preference") if isinstance(signals.get("community_size_preference"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    questions = list(context.get("adaptive_questions") or [])

    if str(community.get("value") or "UNKNOWN").upper() == "UNKNOWN" and not _question_exists(context, "community_size_preference"):
        questions.append(
            _base._question(
                "community_size_preference",
                "Would he prefer a small home-like setting, a medium-sized community, a larger senior community with more people and activities, or no preference?",
                "Community environment can materially change the ordering of otherwise appropriate Assisted Living options. We do not infer this preference from age, mobility, or diagnosis.",
                ["preference_congruence", "social_connection_engagement"],
                ["Small community", "Medium community", "Large community", "No preference"],
            )
        )

    hi = questionnaire_state.get("humanIntelligenceV2") if isinstance(questionnaire_state.get("humanIntelligenceV2"), dict) else {}
    family = hi.get("familyProfile") if isinstance(hi.get("familyProfile"), dict) else {}
    raw_social_answer = _norm(family.get("socialInteractionNeed"))
    social_acknowledged_unknown = raw_social_answer in {"not sure", "unsure", "no preference"}
    if (
        str(social.get("value") or "UNKNOWN").upper() == "UNKNOWN"
        and not social_acknowledged_unknown
        and not _question_exists(context, "social_interaction_preference")
    ):
        questions.append(
            _base._question(
                "social_interaction_preference",
                "How important is it that he have frequent opportunities each day to meet people and join activities?",
                "Social engagement is a material fit factor for Assisted Living. If it is unknown, we ask instead of assuming that a mobile, cognitively intact resident wants either a busy or a quiet environment.",
                ["social_connection_engagement", "social_climate", "preference_congruence"],
                ["Very important", "Somewhat important", "Not important", "No preference", "Not sure"],
            )
        )

    context["adaptive_questions"] = questions
    context["decision_readiness"] = "NEEDS_CLARIFICATION" if questions else "READY"
    context["material_unknown_policy"] = {
        "rule": "ASK_IF_MATERIAL_TO_ELIGIBILITY_ORDERING_TRADEOFF_OR_TRANSITION",
        "assisted_living_profile_detected": True,
        "unknown_is_not_default": True,
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
        raise RuntimeError(
            "Las Vegas person-fit canonical payload checksum mismatch: "
            f"sha256={actual_payload_sha} expected={_base._PERSON_FIT_PAYLOAD_SHA256}"
        )

    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or []
    if payload.get("record_count") != _base._PERSON_FIT_RECORD_COUNT or len(records) != _base._PERSON_FIT_RECORD_COUNT:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 367 source records")
    if payload.get("beds_known_count") != _base._PERSON_FIT_BEDS_KNOWN:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 313 known official bed counts")

    return {
        str(row.get("canonical_id") or ""): row
        for row in records
        if row.get("canonical_id")
    }


def attach_human_person_fit(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> None:
    index = _verified_person_fit_index()
    preference = str(
        (((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")
    ).upper()

    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "")
        evidence = index.get(canonical_id) or {}
        beds = evidence.get("total_bed_count")
        if not isinstance(beds, int):
            beds = None
        band = _base._community_size_band(beds)
        fit = _base._size_fit(preference, band)
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


__all__ = [
    "attach_human_person_fit",
    "build_human_intelligence_context",
    "has_explicit_person_fit_preference",
    "person_fit_sort_key",
]
