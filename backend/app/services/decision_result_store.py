"""Server-owned decision and intake artifacts in the shared application database.

Opaque handles are bound to exact inputs and expire after two hours. Database
errors never issue a handle or silently fall back to a different interpretation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import secrets
import time
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models.decision_artifact import DecisionArtifact

_TTL_SECONDS = 2 * 60 * 60
_SCHEMA_VERSION = 1


class ArtifactStoreUnavailable(RuntimeError):
    """The reviewed profile cannot currently be saved or retrieved."""


def decision_inputs_fingerprint(questionnaire_state: Dict[str, Any], natural_language_query: str, limit: int) -> str:
    canonical = json.dumps(
        {"questionnaire_state": questionnaire_state or {},
         "natural_language_query": (natural_language_query or "").strip(),
         "limit": int(limit or 0)},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def remember_decision_result(result: Dict[str, Any], *, inputs_fingerprint: str) -> str:
    token = secrets.token_urlsafe(24)
    now = time.time()
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False)
    try:
        with SessionLocal() as db:
            db.query(DecisionArtifact).filter(DecisionArtifact.expires_at_epoch <= now).delete(synchronize_session=False)
            db.add(DecisionArtifact(
                token_hash=_token_hash(token), inputs_fingerprint=inputs_fingerprint,
                schema_version=_SCHEMA_VERSION, payload_json=payload,
                created_at_epoch=now, expires_at_epoch=now + _TTL_SECONDS,
            ))
            db.commit()
    except SQLAlchemyError as exc:
        raise ArtifactStoreUnavailable("Unable to save your reviewed profile. Please try again.") from exc
    return token


def recall_decision_result(decision_id: Optional[str], *, inputs_fingerprint: str) -> Optional[Dict[str, Any]]:
    if not decision_id:
        return None
    try:
        with SessionLocal() as db:
            entry = db.get(DecisionArtifact, _token_hash(decision_id))
            if entry is None:
                return None
            if entry.expires_at_epoch <= time.time():
                db.delete(entry)
                db.commit()
                return None
            if entry.schema_version != _SCHEMA_VERSION or not secrets.compare_digest(entry.inputs_fingerprint, inputs_fingerprint):
                return None
            return json.loads(entry.payload_json)
    except SQLAlchemyError as exc:
        raise ArtifactStoreUnavailable("Unable to retrieve your reviewed profile. Please try again.") from exc


def _reset_for_tests() -> None:
    with SessionLocal() as db:
        db.query(DecisionArtifact).delete()
        db.commit()


def intake_inputs_fingerprint(questionnaire_state: Dict[str, Any], natural_language_query: str) -> str:
    state = copy.deepcopy(questionnaire_state)
    # Workflow acknowledgements are not client facts. All care, financial,
    # identity, preference and adaptive-answer fields remain in the fingerprint.
    state.pop("questionnaireCompletion", None)
    state.pop("aiProcessContinuity", None)
    return "intake:" + decision_inputs_fingerprint(state, natural_language_query, 0)


def remember_intake_profile(profile: Dict[str, Any], *, questionnaire_state: Dict[str, Any], natural_language_query: str) -> str:
    from app.services.canonical_decision_state import canonical_client_is_complete, canonical_state_payload
    if not canonical_client_is_complete(profile) or canonical_state_payload(profile).get("system") == "BLOCKED":
        raise ValueError("Only a complete, unblocked server profile can be confirmed")
    return remember_decision_result({
        "artifact_kind": "CONFIRMED_INTAKE_CANDIDATE",
        "profile": profile,
        "questionnaire_state": questionnaire_state,
        "natural_language_query": natural_language_query,
    }, inputs_fingerprint=intake_inputs_fingerprint(questionnaire_state, natural_language_query))


def recall_intake_profile(profile_id: str, *, questionnaire_state: Dict[str, Any], natural_language_query: str) -> Optional[Dict[str, Any]]:
    artifact = recall_decision_result(profile_id, inputs_fingerprint=intake_inputs_fingerprint(questionnaire_state, natural_language_query))
    if not artifact or artifact.get("artifact_kind") != "CONFIRMED_INTAKE_CANDIDATE":
        return None
    return artifact


__all__ = [
    "decision_inputs_fingerprint",
    "recall_decision_result",
    "remember_decision_result",
]
