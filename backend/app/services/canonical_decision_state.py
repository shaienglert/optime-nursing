from __future__ import annotations

"""Canonical single-source decision state for Nursing V2.

This module does not make decisions. It seals already-governed client and facility
facts into immutable downstream packets and validates cross-layer invariants.
Downstream AI/rules consume this state instead of re-parsing raw questionnaire/text.
"""

from copy import deepcopy
from typing import Any, Dict, Iterable, List


_ALLOWED_KNOWLEDGE = {"KNOWN", "UNKNOWN", "AMBIGUOUS", "CONFLICT"}
_ALLOWED_MUST_STATUS = {"PASS", "PENDING_VERIFICATION", "FAIL"}


def _upper(value: Any, default: str = "UNKNOWN") -> str:
    text = str(value or default).strip().upper()
    return text or default


def _client_statement_index(human_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    semantic = human_context.get("semantic_ai") if isinstance(human_context.get("semantic_ai"), dict) else {}
    result = semantic.get("result") if isinstance(semantic.get("result"), dict) else {}
    rows: List[Dict[str, Any]] = []
    for statement in result.get("statements") or []:
        if not isinstance(statement, dict):
            continue
        knowledge = _upper(statement.get("knowledge_state"))
        if knowledge not in _ALLOWED_KNOWLEDGE:
            knowledge = "UNKNOWN"
        rows.append(
            {
                "raw_text": str(statement.get("raw_text") or "").strip(),
                "meaning": str(statement.get("meaning") or "").strip(),
                "importance": _upper(statement.get("importance")),
                "knowledge_state": knowledge,
                "status": _upper(statement.get("status")),
                "mapped_parameters": [str(value) for value in statement.get("mapped_parameters") or []],
                "clarification_question": str(statement.get("clarification_question") or "").strip() or None,
                "research_task": str(statement.get("research_task") or "").strip() or None,
                "provenance": "SEMANTIC_AI_STATEMENT_ACCOUNTING",
            }
        )
    return rows


def build_canonical_client_state(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    decision_intelligence: Dict[str, Any],
) -> Dict[str, Any]:
    """Seal client-owned truth for the current run.

    Strategy/ranking layers may consume this object but must not parse raw input again.
    Raw inputs are retained only as provenance/audit material.
    """
    human = decision_intelligence.get("human_intelligence") if isinstance(decision_intelligence.get("human_intelligence"), dict) else {}
    intent = decision_intelligence.get("client_intent") if isinstance(decision_intelligence.get("client_intent"), dict) else {}
    strategy = decision_intelligence.get("living_strategy") if isinstance(decision_intelligence.get("living_strategy"), dict) else {}
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    semantic_result = semantic.get("result") if isinstance(semantic.get("result"), dict) else {}

    state = {
        "version": "canonical-client-decision-state-v2",
        "sealed_for_downstream": True,
        "raw_input_provenance": {
            "questionnaire_state": deepcopy(questionnaire_state),
            "natural_language_query": str(natural_language_query or ""),
        },
        "statement_accounting": _client_statement_index(human),
        "decision_readiness": _upper(human.get("decision_readiness") or decision_intelligence.get("decision_readiness")),
        "facts": list(semantic_result.get("facts") or []),
        "constraints": list(semantic_result.get("constraints") or []),
        "concerns": list(semantic_result.get("concerns") or []),
        "must_requirements": deepcopy(intent.get("must_haves") or []),
        "nice_preferences": deepcopy((decision_intelligence.get("dynamic_preference_model") or {}).get("preferences") or semantic_result.get("preferences") or []),
        "living_strategies": deepcopy(strategy.get("strategy_candidates") or []),
        "unresolved_client_questions": deepcopy(human.get("adaptive_questions") or []),
        "semantic_governance": deepcopy(semantic_result.get("governance") or {}),
        "downstream_rule": "Do not derive new client facts, MUSTs, NICE preferences, household state or living strategy by parsing raw inputs after this state is sealed.",
    }
    validate_canonical_client_state(state)
    return state


def validate_canonical_client_state(state: Dict[str, Any]) -> None:
    if state.get("sealed_for_downstream") is not True:
        raise RuntimeError("CANONICAL_CLIENT_STATE_NOT_SEALED")
    statements = state.get("statement_accounting") if isinstance(state.get("statement_accounting"), list) else []
    seen = set()
    for index, statement in enumerate(statements):
        if not isinstance(statement, dict):
            raise RuntimeError(f"CANONICAL_CLIENT_INVALID_STATEMENT:{index}")
        identity = (str(statement.get("raw_text") or ""), str(statement.get("meaning") or ""))
        if identity in seen:
            raise RuntimeError(f"CANONICAL_CLIENT_DUPLICATE_STATEMENT:{index}")
        seen.add(identity)
        if _upper(statement.get("knowledge_state")) not in _ALLOWED_KNOWLEDGE:
            raise RuntimeError(f"CANONICAL_CLIENT_INVALID_KNOWLEDGE:{index}")


def build_authoritative_must_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    gate = _upper(fit.get("hard_gate"), "PENDING_VERIFICATION")
    if gate not in _ALLOWED_MUST_STATUS:
        raise RuntimeError(f"CANONICAL_MUST_INVALID_GATE:{gate}")
    passed = sorted({str(value) for value in fit.get("must_pass") or [] if str(value)})
    pending = sorted({str(value) for value in fit.get("must_unknown") or [] if str(value)})
    failed = sorted({str(value) for value in fit.get("must_fail") or [] if str(value)})
    overlap = (set(passed) & set(pending)) | (set(passed) & set(failed)) | (set(pending) & set(failed))
    if overlap:
        raise RuntimeError(f"CANONICAL_MUST_BUCKET_CONFLICT:{','.join(sorted(overlap))}")
    expected = "FAIL" if failed else ("PENDING_VERIFICATION" if pending else "PASS")
    if gate != expected:
        raise RuntimeError(f"CANONICAL_MUST_GATE_CONTRADICTION:{gate}!={expected}")
    return {
        "status": gate,
        "pass": passed,
        "pending_verification": pending,
        "fail": failed,
        "authoritative": True,
        "immutable_downstream": True,
    }


def build_canonical_facility_state(row: Dict[str, Any], governed_claims: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "version": "canonical-facility-evidence-state-v2",
        "canonical_facility_id": row.get("canonical_facility_id"),
        "facility_name": row.get("facility_name"),
        "canonical_type": row.get("canonical_type"),
        "housing_modalities": deepcopy(row.get("housing_modalities") or []),
        "must": build_authoritative_must_snapshot(row),
        "care_setting_fit": deepcopy(row.get("care_setting_fit") or {}),
        "governed_claims": deepcopy(list(governed_claims or [])),
        "source_rule": "Canonical facility evidence and authoritative MUST state are the only downstream facility truth. Sampled claims may limit explanation detail but may not change MUST status.",
    }


def assert_ai_output_respects_authoritative_must(row: Dict[str, Any], information_deficits: Iterable[Any]) -> None:
    """Block downstream AI text that contradicts an authoritative MUST PASS.

    This is intentionally semantic-light: an explicit MUST key appearing in a deficit
    after PASS is enough to fail closed. Future V2 packets should use structured
    deficit capability IDs rather than free text.
    """
    snapshot = build_authoritative_must_snapshot(row)
    passed = set(snapshot["pass"])
    normalized_deficits = " ".join(str(value or "").upper().replace("-", "_") for value in information_deficits)
    aliases = {
        "MEDICATION_SUPPORT_AVAILABLE": ("MEDICATION", "MEDICINE"),
        "ADL_SUPPORT_AVAILABLE": ("ADL", "BATH", "DRESS", "PERSONAL_CARE"),
        "COUPLE_CORESIDENCE": ("COUPLE", "CO_RESID", "CORESID"),
        "REHAB_PATH_AVAILABLE": ("REHAB", "PT", "OT"),
    }
    for key in passed:
        tokens = aliases.get(key, (key,))
        if any(token in normalized_deficits and ("UNKNOWN" in normalized_deficits or "UNVERIFIED" in normalized_deficits or "MISSING" in normalized_deficits) for token in tokens):
            raise RuntimeError(f"AI_DOWNSTREAM_CONTRADICTS_AUTHORITATIVE_MUST:{key}")


__all__ = [
    "build_canonical_client_state",
    "validate_canonical_client_state",
    "build_authoritative_must_snapshot",
    "build_canonical_facility_state",
    "assert_ai_output_respects_authoritative_must",
]
