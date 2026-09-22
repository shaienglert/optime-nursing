"""Server-held decision results, addressed by an opaque decision_id.

The personal report used to accept a full ``decision_result`` from the browser and
trust it (its only "authority" check was an ``authoritative: true`` flag inside the
same client-supplied JSON). A caller could therefore insert a facility that does not
exist and receive an Oomnik-branded report recommending it.

Instead, /decision-engine/recommendations keeps a copy of the exact response it
served and returns a ``decision_id``. A report may reuse that copy only when the id
is known *and* the request's inputs are the ones the decision was computed for.
Anything else (unknown id, expired id, different inputs, another worker process,
a restart) falls back to recomputing on the server -- slower, never wrong.

This is deliberately process-local and bounded: it is a cache of server output, not
a system of record. A persisted, versioned decision artifact is the follow-up.
"""
from __future__ import annotations

import copy
import hashlib
import json
import secrets
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

_MAX_ENTRIES = 256
_TTL_SECONDS = 2 * 60 * 60

_lock = threading.Lock()
_entries: "OrderedDict[str, tuple[float, str, Dict[str, Any]]]" = OrderedDict()


def decision_inputs_fingerprint(questionnaire_state: Dict[str, Any], natural_language_query: str, limit: int) -> str:
    canonical = json.dumps(
        {
            "questionnaire_state": questionnaire_state or {},
            "natural_language_query": (natural_language_query or "").strip(),
            "limit": int(limit or 0),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def remember_decision_result(result: Dict[str, Any], *, inputs_fingerprint: str) -> str:
    decision_id = secrets.token_urlsafe(18)
    now = time.monotonic()
    with _lock:
        _entries[decision_id] = (now, inputs_fingerprint, copy.deepcopy(result))
        _entries.move_to_end(decision_id)
        while len(_entries) > _MAX_ENTRIES:
            _entries.popitem(last=False)
    return decision_id


def recall_decision_result(decision_id: Optional[str], *, inputs_fingerprint: str) -> Optional[Dict[str, Any]]:
    if not decision_id:
        return None
    now = time.monotonic()
    with _lock:
        entry = _entries.get(decision_id)
        if entry is None:
            return None
        stored_at, fingerprint, result = entry
        if now - stored_at > _TTL_SECONDS:
            _entries.pop(decision_id, None)
            return None
        if not secrets.compare_digest(fingerprint, inputs_fingerprint):
            return None
        return copy.deepcopy(result)


def _reset_for_tests() -> None:
    with _lock:
        _entries.clear()


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
