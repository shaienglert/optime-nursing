from __future__ import annotations

"""Dynamic semantic preference model and evidence verification.

This module deliberately knows nothing about specific hobbies, cultures, languages,
religions, amenities, or lifestyle preferences. Semantic AI extracts arbitrary
client preferences from the interview. The verifier may mark a preference MATCH or
MISMATCH only by citing claim IDs that exist in the governed facility evidence
ledger. Missing evidence remains UNKNOWN.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from typing import Any, Dict, List, Tuple

from app.services.semantic_intent_ai import _default_transport


_DERIVED_OR_PRESENTATION_FIELDS = {
    "ai_ranking",
    "nice_to_have_coverage",
    "dynamic_preference_fit",
    "legacy_structured_nice_fit",
    "structured_nice_to_have_coverage",
    "rank_position",
    "rank_display",
    "rank_tie_status",
    "tied_with",
    "explanation",
}


def _stable_id(text: str) -> str:
    digest = hashlib.sha256(text.strip().casefold().encode("utf-8")).hexdigest()[:16]
    return f"pref:{digest}"


def _semantic_result(human_context: Dict[str, Any]) -> Dict[str, Any]:
    semantic = human_context.get("semantic_ai") if isinstance(human_context.get("semantic_ai"), dict) else {}
    result = semantic.get("result") if isinstance(semantic.get("result"), dict) else {}
    return result


def build_dynamic_preference_model(human_context: Dict[str, Any]) -> Dict[str, Any]:
    """Create an open-ended preference model from Semantic AI output.

    No keyword list is used. Any NICE statement or explicit semantic preference can
    become a preference dimension. The original client meaning is preserved.
    """
    result = _semantic_result(human_context)
    raw: List[Tuple[str, str, str]] = []

    for value in result.get("preferences") or []:
        text = str(value or "").strip()
        if text:
            raw.append((text, text, "semantic_ai.preferences"))

    for statement in result.get("statements") or []:
        if not isinstance(statement, dict):
            continue
        if str(statement.get("importance") or "").upper() != "NICE":
            continue
        if str(statement.get("knowledge_state") or "").upper() not in {"KNOWN", "AMBIGUOUS"}:
            continue
        original = str(statement.get("raw_text") or "").strip()
        meaning = str(statement.get("meaning") or original).strip()
        if original or meaning:
            raw.append((original or meaning, meaning or original, "semantic_ai.statements"))

    seen: set[str] = set()
    preferences: List[Dict[str, Any]] = []
    for original, meaning, source in raw:
        canonical_text = meaning.strip()
        dedupe_key = canonical_text.casefold()
        if not canonical_text or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        preferences.append(
            {
                "preference_id": _stable_id(canonical_text),
                "client_expression": original,
                "semantic_meaning": canonical_text,
                "importance": "NICE",
                "source": source,
                "verification_rule": "MATCH requires governed facility evidence that specifically supports this semantic preference; broader or adjacent evidence is insufficient unless it directly entails the preference.",
            }
        )

    return {
        "version": "dynamic-semantic-preferences-v1",
        "owner": "SEMANTIC_AI",
        "preferences": preferences,
        "preference_count": len(preferences),
        "open_world": True,
        "hard_coded_preference_catalog_forbidden": True,
        "unknown_policy": "NO_GOVERNED_EVIDENCE=>UNKNOWN",
    }


def _flatten_claims(value: Any, path: str, out: List[Dict[str, Any]], *, depth: int = 0) -> None:
    if depth > 6 or len(out) >= 240:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if depth == 0 and key_text in _DERIVED_OR_PRESENTATION_FIELDS:
                continue
            child_path = f"{path}.{key_text}" if path else key_text
            _flatten_claims(child, child_path, out, depth=depth + 1)
        return
    if isinstance(value, list):
        for index, child in enumerate(value[:30]):
            _flatten_claims(child, f"{path}[{index}]", out, depth=depth + 1)
        return
    if value is None or isinstance(value, (str, int, float, bool)):
        text = str(value).strip() if value is not None else ""
        if not text or text.upper() == "UNKNOWN":
            return
        claim_id = f"claim:{hashlib.sha256((path + '=' + text).encode('utf-8')).hexdigest()[:18]}"
        out.append({"claim_id": claim_id, "path": path, "value": value})


def build_facility_claim_ledger(row: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the complete governed candidate record into auditable claims.

    New evidence fields automatically enter the ledger. Only derived ranking/UI fields
    are excluded to avoid circular self-evidence. This removes field-by-field wiring.
    """
    governed_record = {
        str(key): value
        for key, value in row.items()
        if str(key) not in _DERIVED_OR_PRESENTATION_FIELDS and not str(key).startswith("__")
    }
    claims: List[Dict[str, Any]] = []
    _flatten_claims(governed_record, "facility", claims)
    return {
        "canonical_facility_id": row.get("canonical_facility_id"),
        "facility_name": row.get("facility_name"),
        "claims": claims,
        "source_model": "COMPLETE_GOVERNED_CANDIDATE_RECORD",
    }


def _verification_prompt(row: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
    ledger = build_facility_claim_ledger(row)
    return {
        "role": "OPTIME_NURSING_SEMANTIC_PREFERENCE_VERIFIER",
        "mission": "Evaluate arbitrary client NICE preferences against the governed evidence ledger for one facility.",
        "rules": [
            "Do not use outside knowledge, brand knowledge, or assumptions.",
            "For every supplied preference return exactly one assessment.",
            "MATCH or MISMATCH requires at least one supporting_claim_id from the supplied ledger.",
            "If the ledger does not specifically resolve the preference, return UNKNOWN.",
            "Do not treat a broad category as proof of a narrower preference unless the cited claim directly entails it.",
            "Some supplied preferences describe a client value, goal, or search-scope decision "
            "(for example 'preserve independence', 'least restrictive setting', or 'include CCRC "
            "options in the search') rather than a checkable fact about this specific facility. No "
            "governed evidence could ever confirm or refute those -- return NOT_APPLICABLE for them, "
            "not UNKNOWN. Use NOT_APPLICABLE only when no facility's evidence could ever resolve the "
            "preference in principle, not merely because this facility's ledger happens to lack it.",
            "Never change MUST eligibility.",
        ],
        "facility": ledger,
        "preferences": model.get("preferences") or [],
        "required_output": {
            "assessments": [
                {
                    "preference_id": "string",
                    "status": "MATCH|MISMATCH|UNKNOWN|NOT_APPLICABLE",
                    "supporting_claim_ids": ["claim:id"],
                    "reason": "string",
                    "provider_question_if_unknown": "string|null",
                }
            ]
        },
    }


def _validate_assessments(packet: Dict[str, Any], row: Dict[str, Any], model: Dict[str, Any]) -> List[Dict[str, Any]]:
    expected = {str(p.get("preference_id")) for p in model.get("preferences") or []}
    ledger = build_facility_claim_ledger(row)
    valid_claims = {str(c.get("claim_id")) for c in ledger.get("claims") or []}
    assessments = packet.get("assessments") if isinstance(packet.get("assessments"), list) else []
    ids = [str(a.get("preference_id") or "") for a in assessments if isinstance(a, dict)]
    if len(ids) != len(expected) or set(ids) != expected or len(set(ids)) != len(ids):
        raise RuntimeError("SEMANTIC_PREFERENCE_CLOSED_WORLD_VIOLATION")

    validated: List[Dict[str, Any]] = []
    for assessment in assessments:
        status = str(assessment.get("status") or "UNKNOWN").upper()
        if status not in {"MATCH", "MISMATCH", "UNKNOWN", "NOT_APPLICABLE"}:
            raise RuntimeError("SEMANTIC_PREFERENCE_INVALID_STATUS")
        supporting = [str(v) for v in assessment.get("supporting_claim_ids") or []]
        if any(claim_id not in valid_claims for claim_id in supporting):
            raise RuntimeError("SEMANTIC_PREFERENCE_UNKNOWN_CLAIM")
        if status in {"MATCH", "MISMATCH"} and not supporting:
            raise RuntimeError("SEMANTIC_PREFERENCE_ASSERTION_WITHOUT_EVIDENCE")
        if status in {"UNKNOWN", "NOT_APPLICABLE"}:
            supporting = []
        validated.append(
            {
                "preference_id": str(assessment.get("preference_id")),
                "status": status,
                "supporting_claim_ids": supporting,
                "reason": str(assessment.get("reason") or ""),
                "provider_question_if_unknown": str(assessment.get("provider_question_if_unknown") or "").strip() or None,
            }
        )
    return validated


def verify_dynamic_preferences(rows: List[Dict[str, Any]], model: Dict[str, Any]) -> Dict[str, Any]:
    preferences = model.get("preferences") if isinstance(model.get("preferences"), list) else []
    if not preferences:
        return {
            "status": "NO_DYNAMIC_PREFERENCES",
            "preference_count": 0,
            "nice_complete_candidate_count": 0,
            "verification_required_count": 0,
        }

    enabled = os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    required = os.getenv("OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    complete = 0
    verification_required = 0
    assessments_by_index: Dict[int, List[Dict[str, Any]]] = {}

    def verify_one(index: int, row: Dict[str, Any]) -> tuple[int, List[Dict[str, Any]]]:
        if not enabled:
            return index, []
        try:
            packet = _default_transport(_verification_prompt(row, model))
            return index, _validate_assessments(packet, row, model)
        except Exception as exc:
            if required:
                raise RuntimeError(f"AI_PREFERENCE_VERIFICATION_REQUIRED_FAILED:{exc}") from exc
            return index, []

    if enabled and rows:
        max_workers = max(1, min(10, int(os.getenv("OPTIME_AI_PREFERENCE_MAX_WORKERS", "5"))))
        with ThreadPoolExecutor(max_workers=min(max_workers, len(rows))) as executor:
            futures = [executor.submit(verify_one, index, row) for index, row in enumerate(rows)]
            for future in as_completed(futures):
                index, assessments = future.result()
                assessments_by_index[index] = assessments

    for index, row in enumerate(rows):
        assessments = assessments_by_index.get(index, [])
        if not assessments:
            assessments = [
                {
                    "preference_id": str(pref.get("preference_id")),
                    "status": "UNKNOWN",
                    "supporting_claim_ids": [],
                    "reason": "No validated semantic preference verification was available.",
                    "provider_question_if_unknown": f"Please verify whether this community satisfies: {pref.get('semantic_meaning')}",
                }
                for pref in preferences
            ]

        # NOT_APPLICABLE preferences (client values/goals/search-scope, not checkable
        # facts about this facility) never block completeness -- no facility's
        # evidence could ever resolve them, so requiring a MATCH on them would make
        # NICE_COMPLETE permanently unreachable for any query that contains one.
        checkable_statuses = [status for status in (a["status"] for a in assessments) if status != "NOT_APPLICABLE"]
        if not checkable_statuses or all(status == "MATCH" for status in checkable_statuses):
            coverage = "NICE_COMPLETE"
            complete += 1
        elif any(status == "MATCH" for status in checkable_statuses):
            coverage = "NICE_PARTIAL"
            verification_required += 1
        else:
            coverage = "NICE_UNVERIFIED"
            verification_required += 1

        row["dynamic_preference_fit"] = {
            "status": coverage,
            "assessments": assessments,
            "required_preference_ids": [str(pref.get("preference_id")) for pref in preferences],
        }
        row["nice_to_have_coverage"] = {
            "status": coverage,
            "required": [str(pref.get("preference_id")) for pref in preferences],
            "verified_match": [a["preference_id"] for a in assessments if a["status"] == "MATCH"],
            "unresolved": [a["preference_id"] for a in assessments if a["status"] not in {"MATCH", "NOT_APPLICABLE"}],
            "verified_match_count": sum(1 for a in assessments if a["status"] == "MATCH"),
            "required_count": len(preferences),
            "source": "DYNAMIC_SEMANTIC_PREFERENCE_MODEL",
        }

    return {
        "status": "VERIFIED" if enabled else "AI_UNAVAILABLE_UNKNOWN_PRESERVED",
        "preference_count": len(preferences),
        "nice_complete_candidate_count": complete,
        "verification_required_count": verification_required,
        "verification_execution": "PARALLEL_PER_SELECTED_CANDIDATE" if enabled and rows else "NO_LIVE_AI_VERIFICATION",
        "verification_worker_count": min(max(1, int(os.getenv("OPTIME_AI_PREFERENCE_MAX_WORKERS", "5"))), len(rows)) if enabled and rows else 0,
        "rule": "Any client NICE preference may exist without code changes. MATCH/MISMATCH requires governed claim evidence; otherwise UNKNOWN.",
    }


__all__ = [
    "build_dynamic_preference_model",
    "build_facility_claim_ledger",
    "verify_dynamic_preferences",
]
