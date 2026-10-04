"""Shared NTH change contract used by both advisor simulations and accepted searches.

Consent is a UI control, never an AI-extracted fact. It is bound to the exact source
answers. Only an existing NICE criterion can be waived; MUST, care, budget, location,
availability and facility evidence are never edited here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

IMPLICIT = {"BUDGET_FIT", "AVAILABILITY_FIT"}
NEARBY = "NEARBY_PLACES"
LABELS = {
    "COMMUNITY_ENVIRONMENT_MATCH": "Community size", "PREFERRED_LANGUAGE_SUPPORT": "Preferred language",
    "CONTINUUM_OF_CARE": "Future care continuity", "RICH_CULTURE_AND_ACTIVITIES": "Culture and activities",
    "CLASSICAL_MUSIC_ACCESS": "Classical music", "TRANSPORTATION_AND_OUTINGS": "Transportation and outings",
    "DINING_EXPERIENCE": "Dining experience", "KOSHER_MEALS": "Kosher meals",
    "SOCIAL_INTERACTION_FREQUENCY": "Social interaction frequency", NEARBY: "Nearby amenities",
}
PROTECTED = {
    "PREFERRED_LANGUAGE_SUPPORT": {"REQUIRED_LANGUAGE_SUPPORT", "SEMANTIC_LANGUAGE_SUPPORT"},
    "CONTINUUM_OF_CARE": {"CONTINUUM_OF_CARE_REQUIRED", "SEMANTIC_FUTURE_CARE_PATH"},
    "KOSHER_MEALS": {"SEMANTIC_KOSHER_DIET"},
    "RICH_CULTURE_AND_ACTIVITIES": {"REQUIRED_ACTIVITIES", "SEMANTIC_SOCIAL_DELIVERY"},
    "CLASSICAL_MUSIC_ACCESS": {"REQUIRED_ACTIVITIES"},
}

def safe_nth_keys(intent: dict, profile: dict) -> set[str]:
    must = {str(item.get("key") or "") for item in intent.get("must_haves") or [] if isinstance(item, dict)}
    nice = {str(item.get("key") or "") for item in intent.get("nice_to_haves") or [] if isinstance(item, dict)}
    if profile.get("nearbyPlaces") and profile.get("nearbyPlacesImportance") in {"Important", "Nice to have"}:
        nice.add(NEARBY)
    safe = {key for key in nice - must - IMPLICIT - {""} if not must & PROTECTED.get(key, set())}
    hi = profile.get("humanIntelligenceV2") or {}
    required = {"required", "requirement", "must"}
    if str((hi.get("languageProfile") or {}).get("languageNeedScope") or "").lower() in required:
        safe.discard("PREFERRED_LANGUAGE_SUPPORT")
    if str((hi.get("culturalProfile") or {}).get("kosherRequirements") or "").lower() in required:
        safe.discard("KOSHER_MEALS")
    future = hi.get("futureCareProfile") or {}
    if any(str(value or "").lower() in required for value in (
            future.get("continuumOfCarePreference"), future.get("avoidFutureMovesPreference"), profile.get("futureCarePreference"))):
        safe.discard("CONTINUUM_OF_CARE")
    return safe

def acceptance_for(key: str, intent: dict, profile: dict) -> dict:
    source = {k: v for k, v in profile.items() if k != "questionnaireCompletion" and not k.startswith("_")}
    wire = json.dumps({"parameter": key, "answers": source, "must": intent.get("must_haves") or [],
                       "nice": [item for item in intent.get("nice_to_haves") or [] if item.get("key") == key]},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {"parameter": key, "input_fingerprint": hashlib.sha256(wire.encode()).hexdigest()}

def remove_nice(row: dict, key: str) -> None:
    fit = row.get("client_intent_fit") or {}
    known = key in (fit.get("nice_match") or []) or key in (fit.get("nice_mismatch") or [])
    unknown = key in (fit.get("nice_unknown") or [])
    for field, removed in (("relevant_evidence_known_count", known), ("relevant_evidence_unknown_count", unknown)):
        if isinstance(fit.get(field), int):
            fit[field] = max(0, fit[field] - int(removed))
    for field in ("nice_match", "nice_mismatch", "nice_unknown"):
        fit[field] = [item for item in fit.get(field) or [] if item != key]
    (fit.get("nice_fit_scores") or {}).pop(key, None)

def waive_nth(row: dict, key: str) -> None:
    remove_nice(row, key)
    if key == "COMMUNITY_ENVIRONMENT_MATCH":
        size = (row.get("human_person_fit") or {}).get("community_size") or {}
        size.update({"preference": "NO_PREFERENCE", "fit_score": "UNKNOWN"})
    elif key == NEARBY:
        original = deepcopy(row.get("nearby_place_fit") or {})
        row["nearby_place_fit"] = {"status": "PREFERENCE_WAIVED", "importance": "No preference", "original_fit": original}

def apply_accepted_nth_changes(rows: list[dict], intent: dict, profile: dict, accepted: object) -> dict:
    safe, applied, ignored = safe_nth_keys(intent, profile), [], []
    if not isinstance(accepted, list):
        return {"applied": [], "ignored": [], "must_changed": False}
    for record in accepted[:50]:
        if not isinstance(record, dict):
            continue
        key = str(record.get("parameter") or "")
        if key in applied:
            continue
        if key not in safe or record != acceptance_for(key, intent, profile):
            ignored.append(key)
            continue
        for row in rows:
            waive_nth(row, key)
        applied.append(key)
    return {"applied": applied, "ignored": ignored, "must_changed": False,
            "policy": "EXPLICIT_CLIENT_CONSENT_EXISTING_NTH_ONLY"}
