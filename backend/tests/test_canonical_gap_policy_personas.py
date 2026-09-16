from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


def _statement(*, raw_text: str, mapped_parameters: list[str], question: str) -> dict:
    return {
        "raw_text": raw_text,
        "meaning": raw_text,
        "importance": "MUST",
        "knowledge_state": "AMBIGUOUS",
        "status": "ASKED",
        "mapped_parameters": mapped_parameters,
        "clarification_question": question,
        "research_task": None,
    }


def _packet(*, readiness: str, question: str | None = None, statement: dict | None = None) -> dict:
    return {
        "facts": [],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [statement] if statement else [],
        "next_question": question,
        "research_requests": [],
        "decision_readiness": readiness,
    }


def _run(query: str, ai_packet: dict, state: dict) -> dict:
    with patch.dict(
        os.environ,
        {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"},
        clear=False,
    ), patch(
        "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
        return_value=ai_packet,
    ):
        return build_human_intelligence_context(state, query)


def _couple_case() -> tuple[str, dict]:
    return (
        "A married couple is moving in Las Vegas. One spouse is independent and the other needs daily personal care. "
        "Their combined monthly budget is $11,000.",
        {"budget": 11000, "locationCity": "Las Vegas", "relationship": "Spouse"},
    )


def _widow_case() -> tuple[str, dict]:
    return (
        "A recently widowed woman wants senior living in Las Vegas. She is mentally alert, mobile, and wants company. "
        "Her monthly budget is $8,000.",
        {"budget": 8000, "locationCity": "Las Vegas", "relationship": "Mother"},
    )


class CanonicalGapPolicyPersonaTests(unittest.TestCase):
    def test_explicit_rehab_and_personal_care_facts_resolve_rehab_gap_before_ai_can_block(self) -> None:
        query = (
            "My father recently had a stroke. He needs hands-on help with bathing, dressing and transfers, "
            "medication management, and PT, OT and speech therapy. We need Las Vegas and can spend $17,000 monthly."
        )
        state = {"budget": 17000, "referenceLocationValue": "Las Vegas", "medicareStatus": "Not sure"}
        question = "Does he need skilled PT, OT or speech rehabilitation, personal-care help, or both?"
        asking = _packet(
            readiness="NEEDS_CLARIFICATION",
            question=question,
            statement=_statement(
                raw_text="The rehabilitation level is unclear.",
                mapped_parameters=["rehab_level_needed"],
                question=question,
            ),
        )

        context = _run(query, asking, state)

        self.assertEqual("READY", context["decision_readiness"])
        self.assertEqual([], context["adaptive_questions"])
        self.assertIn("rehab_level_needed", context["canonical_gap_policy"]["resolved_gap_keys"])
        self.assertNotIn("rehab_level_needed", context["canonical_gap_policy"]["blocking_gap_keys"])

    def test_couple_readiness_is_identical_when_ai_invents_cohabitation_clarification(self) -> None:
        query, state = _couple_case()
        question = "Must they share one apartment, or is living on the same campus enough?"
        asking = _packet(
            readiness="NEEDS_CLARIFICATION",
            question=question,
            statement=_statement(
                raw_text="The preferred co-residence arrangement is not stated.",
                mapped_parameters=["cohabitation_requirement"],
                question=question,
            ),
        )
        ready = _packet(readiness="READY")

        asking_context = _run(query, asking, state)
        ready_context = _run(query, ready, state)

        self.assertEqual("READY", asking_context["decision_readiness"])
        self.assertEqual(asking_context["decision_readiness"], ready_context["decision_readiness"])
        self.assertEqual([], asking_context["adaptive_questions"])
        self.assertEqual(asking_context["adaptive_questions"], ready_context["adaptive_questions"])
        assessment = asking_context["canonical_gap_policy"]["assessments"]
        self.assertTrue(any(row["gap_key"] == "cohabitation_requirement" and row["classification"] == "IMPORTANT_NON_BLOCKING" for row in assessment))
    def test_widow_readiness_is_identical_when_ai_invents_loneliness_clarification(self) -> None:
        query, state = _widow_case()
        question = "How severe is her loneliness since the loss?"
        asking = _packet(
            readiness="NEEDS_CLARIFICATION",
            question=question,
            statement=_statement(
                raw_text="The severity of loneliness is not stated.",
                mapped_parameters=["loneliness_severity"],
                question=question,
            ),
        )
        ready = _packet(readiness="READY")

        asking_context = _run(query, asking, state)
        ready_context = _run(query, ready, state)

        self.assertEqual("READY", asking_context["decision_readiness"])
        self.assertEqual(asking_context["decision_readiness"], ready_context["decision_readiness"])
        self.assertEqual([], asking_context["adaptive_questions"])
        self.assertEqual(asking_context["adaptive_questions"], ready_context["adaptive_questions"])
        assessment = asking_context["canonical_gap_policy"]["assessments"]
        self.assertTrue(any(row["gap_key"] == "loneliness_severity" and row["classification"] == "IMPORTANT_NON_BLOCKING" for row in assessment))
    def test_explicit_same_home_requirement_makes_couple_gap_blocking(self) -> None:
        query, state = _couple_case()
        query += " Staying in the same apartment is mandatory for them."
        question = "Can the community safely support both care levels in the same apartment?"
        asking = _packet(
            readiness="NEEDS_CLARIFICATION",
            question=question,
            statement=_statement(
                raw_text="Whether both care levels can be supported in one apartment is unresolved.",
                mapped_parameters=["cohabitation_requirement"],
                question=question,
            ),
        )

        context = _run(query, asking, state)

        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])
        self.assertEqual(1, len(context["adaptive_questions"]))
        assessment = context["canonical_gap_policy"]["assessments"]
        self.assertTrue(any(row["gap_key"] == "cohabitation_requirement" and row["classification"] == "BLOCKING" for row in assessment))
    def test_loneliness_only_escalates_from_deterministic_safety_language(self) -> None:
        query, state = _widow_case()
        query += " She says she may harm herself and is not safe alone tonight."
        ready = _packet(readiness="READY")

        context = _run(query, ready, state)

        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])
        self.assertTrue(context["canonical_gap_policy"]["escalation_required"])
        self.assertEqual("EXPLICIT_IMMEDIATE_SAFETY_RISK", context["canonical_gap_policy"]["escalation_reason"])


if __name__ == "__main__":
    unittest.main()
