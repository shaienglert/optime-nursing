"""Evidence-conservation guard across AI packet repair, independent of care type.

This does not extract or infer facts. It ensures that an already recognized,
source-grounded fact cannot disappear during retries or normalization. The
existing canonical field contract separately checks the concrete extracted
value and its source.
"""
from __future__ import annotations

from typing import Any


def _normalized(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _paths(statement: dict) -> set[str]:
    return {
        str(path).strip()
        for path in (statement.get("mapped_parameters") or [])
        if isinstance(path, str) and path.strip()
    }


def _leaf(obj: dict, path: str) -> Any:
    value: Any = obj
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _has_value(packet: dict, state: dict, path: str) -> bool:
    from app.services.canonical_structured_profile import in_schema
    if not in_schema(path):
        return False
    for source in (packet.get("questionnaire_patch") or {}, state):
        value = _leaf(source, path)
        if value is None or value == "" or value == [] or value == {}:
            continue
        # Unknown/unanswered cannot satisfy a recognized explicit fact.
        if isinstance(value, str) and _normalized(value) in {
            "not sure", "unknown", "not specified", "unanswered",
        }:
            continue
        return True
    return False


def check_recognized_fact_conservation(
    initial: dict, final: dict, *, user_text: str,
    questionnaire_state: dict | None = None,
) -> None:
    """Reject dropped source-grounded facts; never fabricate field values.

    An initially recognized canonical mapping must be materialized in the
    accepted result, or its exact fact must remain explicitly unresolved in a
    meaningful ASKED / RESEARCH_REQUIRED trace. A failed correction remains a
    validation error, not a silent success.
    """
    state = questionnaire_state or {}
    source_text = _normalized(user_text)
    initial_statements = initial.get("statements") or []
    final_statements = final.get("statements") or []
    errors: list[str] = []
    for old in initial_statements:
        if not isinstance(old, dict):
            continue
        # Preserve recognized facts and unresolved research signals alike.
        # Only explicit source-grounded entries are covered here; new user text
        # comprehension itself belongs to the interpretation/coverage contract.
        if old.get("status") not in {"USED", "RESEARCH_REQUIRED"}:
            continue
        if old.get("knowledge_state") not in {"KNOWN", "AMBIGUOUS", "UNKNOWN"}:
            continue
        raw = str(old.get("raw_text") or "").strip()
        if not raw or not source_text or _normalized(raw) not in source_text:
            # Existing button/selection traces are already governed by the
            # selected-property contract, not newly extracted user_text.
            continue
        # Compare literal original quote, not model-authored paraphrases.
        matching = [
            row for row in final_statements
            if isinstance(row, dict) and _normalized(row.get("raw_text")) == _normalized(raw)
        ]
        if not matching:
            errors.append("DROPPED_RECOGNIZED_STATEMENT")
            continue
        if old.get("status") != "USED" or old.get("knowledge_state") != "KNOWN":
            continue
        for path in sorted(_paths(old)):
            from app.services.canonical_structured_profile import in_schema
            if not in_schema(path):
                # This guard cannot promote arbitrary paths into authority.
                continue
            if _has_value(final, state, path) and any(
                path in _paths(item) and item.get("status") == "USED"
                and item.get("knowledge_state") == "KNOWN"
                for item in matching
            ):
                continue
            explicitly_unresolved = any(
                item.get("status") == "ASKED"
                and str(item.get("clarification_question") or "").strip()
                or item.get("status") == "RESEARCH_REQUIRED"
                and str(item.get("research_task") or "").strip()
                for item in matching
            )
            if not explicitly_unresolved:
                # A model may claim a canonical mapping without ever supplying
                # a supported field value. The mapping itself is NOT proof of
                # that detail (e.g. a frequency/center never named by family).
                # Preserve the actual quote and the unresolved path for review,
                # never invent a value or credit a MUST match to the provider.
                # A value that WAS materialized and then disappeared remains a
                # hard loss below, including for any clinical MUST.
                if (
                    old.get("importance") in {"NICE", "CONTEXT"}
                    and not _has_value(initial, state, path)
                    and any(item.get("status") == "USED" for item in matching)
                ):
                    pending = {
                        "raw_text": raw,
                        "rejected_path": path,
                        "importance": old.get("importance"),
                        "status": "PRESERVED_UNMAPPED_NOT_DECISION_EVIDENCE",
                    }
                    records = final.setdefault("unmapped_recognized_facts", [])
                    if pending not in records:
                        records.append(pending)
                    continue
                errors.append("DROPPED_RECOGNIZED_FIELD:" + path)
    if errors:
        raise RuntimeError("SEMANTIC_AI_FACT_LOSS:" + ",".join(sorted(set(errors))))
