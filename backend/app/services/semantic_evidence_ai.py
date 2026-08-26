from __future__ import annotations

"""Semantic interpretation of provider evidence.

The AI understands arbitrary provider wording; the Guardian owns the allowed
canonical capability schema and decides whether the interpreted service level is
sufficient. The model may never create a facility fact without supplied source text.
"""

import os
from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


CAPABILITY_SCHEMA: Dict[str, Dict[str, Any]] = {
    "MEDICATION_SUPPORT": {
        "levels": [
            "NONE_OR_NOT_STATED",
            "REMINDER_ONLY",
            "SELF_ADMIN_ASSISTANCE",
            "MANAGEMENT_OR_SUPERVISION",
            "ADMINISTRATION_BY_STAFF",
        ],
        "must_sufficient_levels": [
            "SELF_ADMIN_ASSISTANCE",
            "MANAGEMENT_OR_SUPERVISION",
            "ADMINISTRATION_BY_STAFF",
        ],
        "guardrail": "Reminder-only wording is not sufficient evidence of medication-management support.",
    },
    "ADL_SUPPORT": {
        "levels": ["NONE_OR_NOT_STATED", "GENERAL_PERSONAL_CARE", "SPECIFIC_ADL_ASSISTANCE"],
        "must_sufficient_levels": ["SPECIFIC_ADL_ASSISTANCE"],
        "guardrail": "General personal-care language does not prove a specific ADL unless the source supports it.",
    },
    "TRANSPORTATION": {
        "levels": ["NONE_OR_NOT_STATED", "LIMITED_OR_APPOINTMENT", "SCHEDULED_COMMUNITY_TRANSPORT"],
        "must_sufficient_levels": ["LIMITED_OR_APPOINTMENT", "SCHEDULED_COMMUNITY_TRANSPORT"],
    },
    "DINING": {
        "levels": ["NONE_OR_NOT_STATED", "DINING_AVAILABLE", "MEAL_SERVICE_EXPLICIT"],
        "must_sufficient_levels": ["DINING_AVAILABLE", "MEAL_SERVICE_EXPLICIT"],
    },
    "REHAB": {
        "levels": ["NONE_OR_NOT_STATED", "EXTERNAL_PATH", "ONSITE_THERAPY", "SKILLED_REHAB"],
        "must_sufficient_levels": ["EXTERNAL_PATH", "ONSITE_THERAPY", "SKILLED_REHAB"],
    },
    "COUPLE_CORESIDENCE": {
        "levels": ["NONE_OR_NOT_STATED", "POSSIBLE", "EXPLICITLY_SUPPORTED"],
        "must_sufficient_levels": ["EXPLICITLY_SUPPORTED"],
    },
    "OUTSIDE_CARE": {
        "levels": ["NONE_OR_NOT_STATED", "POSSIBLE_BUT_UNCONFIRMED", "EXPLICITLY_ALLOWED"],
        "must_sufficient_levels": ["EXPLICITLY_ALLOWED"],
    },
    "CONTINUUM_OF_CARE": {
        "levels": ["NONE_OR_NOT_STATED", "MULTIPLE_CARE_LEVELS", "LIFE_PLAN_CONTINUUM"],
        "must_sufficient_levels": ["MULTIPLE_CARE_LEVELS", "LIFE_PLAN_CONTINUUM"],
    },
    "SOCIAL_ENGAGEMENT": {
        "levels": ["NONE_OR_NOT_STATED", "GENERAL_ACTIVITIES", "RICH_PROGRAMMING"],
        "must_sufficient_levels": ["GENERAL_ACTIVITIES", "RICH_PROGRAMMING"],
    },
}


def _enabled() -> bool:
    return os.getenv("OPTIME_SEMANTIC_EVIDENCE_AI_ENABLED", os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0")).strip().lower() in {"1", "true", "yes", "on"}


def _required() -> bool:
    return os.getenv("OPTIME_SEMANTIC_EVIDENCE_AI_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}


def _prompt(*, facility_name: str, city: str, source_url: str, source_text: str, requested_parameters: List[str]) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_SEMANTIC_EVIDENCE_INTERPRETER",
        "mission": "Interpret the supplied official-provider source text semantically. Map what the source actually proves to the closed canonical capability schema. Do not rely on exact keywords and do not infer services from brand, facility type, or general expectations.",
        "rules": [
            "Use only supplied source_text; outside knowledge is forbidden.",
            "A capability not supported by the supplied text must be NONE_OR_NOT_STATED.",
            "Do not treat a broader phrase as proof of a narrower service unless the wording entails it.",
            "Medication reminders alone are REMINDER_ONLY and do not prove medication management or administration.",
            "General personal care does not prove bathing or dressing assistance unless the text supports those ADLs.",
            "Return every canonical capability exactly once.",
            "evidence_summary must be a concise paraphrase of the source support, not an invented claim.",
            "confidence measures interpretation confidence, not facility quality.",
        ],
        "facility": {"name": facility_name, "city": city},
        "source_url": source_url,
        "requested_parameters": requested_parameters,
        "canonical_capability_schema": CAPABILITY_SCHEMA,
        "source_text": source_text[:30000],
        "required_output": {
            "capabilities": [
                {
                    "capability": "one canonical capability key",
                    "level": "one allowed level for that capability",
                    "evidence_summary": "short paraphrase",
                    "confidence": "HIGH|MEDIUM|LOW",
                }
            ]
        },
    }


def _validate(packet: Dict[str, Any]) -> Dict[str, Any]:
    raw = packet.get("capabilities") if isinstance(packet.get("capabilities"), list) else []
    by_key: Dict[str, Dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("capability") or "").strip().upper()
        if key not in CAPABILITY_SCHEMA or key in by_key:
            continue
        level = str(item.get("level") or "").strip().upper()
        if level not in CAPABILITY_SCHEMA[key]["levels"]:
            raise RuntimeError(f"SEMANTIC_EVIDENCE_INVALID_LEVEL:{key}:{level}")
        confidence = str(item.get("confidence") or "LOW").strip().upper()
        if confidence not in {"HIGH", "MEDIUM", "LOW"}:
            confidence = "LOW"
        by_key[key] = {
            "capability": key,
            "level": level,
            "evidence_summary": str(item.get("evidence_summary") or "").strip()[:500],
            "confidence": confidence,
            "guardian_must_sufficient": level in CAPABILITY_SCHEMA[key].get("must_sufficient_levels", []),
        }
    missing = [key for key in CAPABILITY_SCHEMA if key not in by_key]
    if missing:
        raise RuntimeError("SEMANTIC_EVIDENCE_INCOMPLETE_CLOSED_WORLD:" + ",".join(missing))
    return {
        "status": "AI_SEMANTIC_EVIDENCE_INTERPRETED",
        "closed_world_validated": True,
        "capabilities": [by_key[key] for key in CAPABILITY_SCHEMA],
    }


def interpret_facility_evidence_with_ai(
    *,
    facility_name: str,
    city: str,
    source_url: str,
    source_text: str,
    requested_parameters: List[str] | None = None,
    transport: Callable[[Dict[str, Any]], Dict[str, Any]] = _default_transport,
) -> Dict[str, Any]:
    if not _enabled():
        return {"status": "DISABLED", "closed_world_validated": False, "capabilities": []}
    try:
        packet = transport(
            _prompt(
                facility_name=facility_name,
                city=city,
                source_url=source_url,
                source_text=source_text,
                requested_parameters=list(requested_parameters or []),
            )
        )
        return _validate(packet)
    except Exception as exc:
        if _required():
            raise RuntimeError(f"SEMANTIC_EVIDENCE_AI_REQUIRED_FAILED:{exc}") from exc
        return {"status": "AI_UNAVAILABLE", "closed_world_validated": False, "capabilities": [], "error": str(exc)[:300]}


def capability_map(interpretation: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("capability")): item
        for item in interpretation.get("capabilities") or []
        if isinstance(item, dict) and str(item.get("capability") or "")
    }


__all__ = ["CAPABILITY_SCHEMA", "capability_map", "interpret_facility_evidence_with_ai"]
