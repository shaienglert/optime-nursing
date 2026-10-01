"""Test double for the one legitimate road from free text to a decision fact.

Owner rule (2026-10-01): once the Canonical Structured Profile exists, no downstream
component may derive a new fact from raw text. The interpreter (semantic AI) reads the
text; its ``questionnaire_patch`` becomes AI_EXTRACTED fields of the Structured Profile
(``build_structured_profile``), and every decision fact is materialized from that profile.

Tests that protect "this sentence becomes that need" therefore supply the interpreter's
packet here instead of relying on a regex. Whether the live model actually produces the
packet for the sentence is the responsibility of the Live Golden Interpreter set.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Iterator, List
from unittest.mock import patch

INTERPRETER_TARGET = "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai"
AI_OFF = {"OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_SEMANTIC_AI_REQUIRED": "0"}


def statement(raw_text: str, mapped: Iterable[str], *, knowledge_state: str = "KNOWN", importance: str = "MUST") -> Dict[str, Any]:
    return {
        "raw_text": raw_text,
        "meaning": raw_text,
        "importance": importance,
        "knowledge_state": knowledge_state,
        "status": "USED",
        "gap_key": None,
        "mapped_parameters": list(mapped),
        "clarification_question": None,
        "research_task": None,
    }


def interpreter_packet(questionnaire_patch: Dict[str, Any], statements: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "decision_readiness": "READY",
        "next_question": None,
        "facts": [],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "research_requests": [],
        "statements": list(statements or []),
        "questionnaire_patch": questionnaire_patch,
    }


@contextmanager
def interpreter_returning(packet: Dict[str, Any]) -> Iterator[Any]:
    """Run with the interpreter enabled and answering ``packet`` for any text."""
    with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "0"}, clear=False):
        with patch(INTERPRETER_TARGET, return_value=packet) as interpreter:
            yield interpreter


@contextmanager
def interpreter_off() -> Iterator[None]:
    with patch.dict(os.environ, AI_OFF, clear=False):
        yield


def need_values(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {row["parameter_id"]: row.get("desired_value") for row in profile.get("needs") or []}


def decision_facts(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Every decision fact the needs profile carries (needs, MUSTs, NICEs, location)."""
    intent = profile.get("client_intent") or {}
    return {
        "needs": sorted((row.get("parameter_id"), row.get("requirement_level"), str(row.get("desired_value"))) for row in profile.get("needs") or []),
        "musts": sorted(str(row.get("key")) for row in intent.get("must_haves") or []),
        "nices": sorted(str(row.get("key")) for row in intent.get("nice_to_haves") or []),
        "location": profile.get("location_city"),
        "decision_questionnaire": {k: v for k, v in (profile.get("canonical_decision_questionnaire") or {}).items()},
    }
