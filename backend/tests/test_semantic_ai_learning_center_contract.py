from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

import requests

from app.services.semantic_intent_ai import _request_with_retry, interpret_client_intent_with_ai
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class SemanticAiLearningCenterContractTests(unittest.TestCase):
    def test_ai_prompt_contains_rules_and_learning_center_advice(self) -> None:
        captured = {}

        def transport(payload):
            captured.update(payload)
            return {
                "facts": ["75-year-old widow", "currently independent", "does not cook"],
                "preferences": ["luxury", "social life", "games"],
                "constraints": ["gluten allergy"],
                "concerns": [],
                "implications": [
                    {
                        "derived_from": ["gluten allergy", "does not cook"],
                        "implication": "Reliable daily gluten-free meal provision may be a MUST",
                        "certainty": "LIKELY",
                        "requires_confirmation": True,
                    }
                ],
                "statements": [
                    {
                        "raw_text": "gluten allergy",
                        "meaning": "dietary safety constraint",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["diet.gluten_free"],
                        "clarification_question": None,
                        "research_task": None,
                    },
                    {
                        "raw_text": "does not cook",
                        "meaning": "depends on provided meals",
                        "importance": "MUST",
                        "knowledge_state": "AMBIGUOUS",
                        "status": "ASKED",
                        "mapped_parameters": ["meals.daily_provision"],
                        "clarification_question": "Do you need all daily meals provided by the community?",
                        "research_task": None,
                    },
                ],
                "next_question": "Do you need all daily meals provided by the community?",
                "research_requests": [],
                "decision_readiness": "NEEDS_CLARIFICATION",
            }

        learning = {
            "advisor": "OPTIME_NURSING_LEARNING_CENTER",
            "consulted": True,
            "agent_count": 10,
            "available_agent_count": 10,
            "agents": [{"agent_key": "nutrition_intelligence", "status": "AVAILABLE", "knowledge": "gluten-free evidence"}],
            "policy": {},
        }
        with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value=learning):
            result = interpret_client_intent_with_ai(
                user_text="75-year-old widow, independent, luxury, social, games, gluten allergy, does not cook",
                questionnaire_state={},
                transport=transport,
            )

        self.assertEqual("OPTIME_NURSING_EXPERT_SEMANTIC_INTERPRETER", captured["role"])
        self.assertTrue(captured["learning_center_advice"]["consulted"])
        self.assertGreaterEqual(len(captured["rules"]), 8)
        self.assertTrue(result["governance"]["ai_based"])
        self.assertTrue(result["governance"]["learning_center_consulted"])
        self.assertEqual(100.0, result["statement_coverage_percent"])
        self.assertEqual(0, result["dropped_statement_count"])
        self.assertEqual("NEEDS_CLARIFICATION", result["decision_readiness"])

    def test_required_ai_cannot_silently_disable(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            context = build_human_intelligence_context({}, "I want a luxury community with strong social life")
        self.assertEqual("REQUIRED_BUT_DISABLED", context["semantic_ai"]["status"])
        self.assertEqual("NEEDS_RESEARCH", context["decision_readiness"])

    def test_invalid_ai_cannot_claim_ready_with_unresolved_statement(self) -> None:
        bad = {
            "statements": [
                {
                    "raw_text": "unknown preference",
                    "meaning": "unknown",
                    "importance": "UNKNOWN",
                    "knowledge_state": "UNKNOWN",
                    "status": "ASKED",
                    "mapped_parameters": [],
                    "clarification_question": "What do you mean?",
                    "research_task": None,
                }
            ],
            "decision_readiness": "READY",
        }
        learning = {"advisor": "OPTIME_NURSING_LEARNING_CENTER", "consulted": True, "agent_count": 1, "available_agent_count": 1, "agents": [], "policy": {}}
        with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value=learning):
            with self.assertRaisesRegex(RuntimeError, "READY_WITH_UNRESOLVED"):
                interpret_client_intent_with_ai(user_text="unknown preference", questionnaire_state={}, transport=lambda _: bad)

    def test_transport_retries_timeout_before_failing_closed(self) -> None:
        response = Mock()
        response.ok = True
        with patch.dict(
            os.environ,
            {
                "OPTIME_SEMANTIC_AI_TIMEOUT_SECONDS": "45",
                "OPTIME_SEMANTIC_AI_MAX_ATTEMPTS": "2",
                "OPTIME_SEMANTIC_AI_RETRY_BACKOFF_SECONDS": "0",
            },
            clear=False,
        ):
            with patch("app.services.semantic_intent_ai.requests.post", side_effect=[requests.Timeout("first"), response]) as post:
                actual = _request_with_retry("https://example.invalid/responses", {"Content-Type": "application/json"}, {"model": "test"})
        self.assertIs(response, actual)
        self.assertEqual(2, post.call_count)
        self.assertEqual((10.0, 45.0), post.call_args.kwargs["timeout"])

    def test_transport_exhaustion_is_explicit(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPTIME_SEMANTIC_AI_TIMEOUT_SECONDS": "45",
                "OPTIME_SEMANTIC_AI_MAX_ATTEMPTS": "2",
                "OPTIME_SEMANTIC_AI_RETRY_BACKOFF_SECONDS": "0",
            },
            clear=False,
        ):
            with patch("app.services.semantic_intent_ai.requests.post", side_effect=requests.Timeout("still slow")):
                with self.assertRaisesRegex(RuntimeError, "SEMANTIC_AI_TRANSPORT_RETRY_EXHAUSTED:attempts=2:timeout=45.0"):
                    _request_with_retry("https://example.invalid/responses", {"Content-Type": "application/json"}, {"model": "test"})


if __name__ == "__main__":
    unittest.main()
