from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class ThreePersonaSemanticDecisionBenchmark(unittest.TestCase):
    def _run(self, query: str, ai_result: dict, state: dict | None = None) -> dict:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result):
                return build_human_intelligence_context(state or {}, query)

    def test_independent_couple_preserves_food_gardens_activities_outings_and_future_care(self) -> None:
        query = (
            "Married independent couple wants senior living in Las Vegas for future care security. "
            "Excellent food is very important, they love activities, well maintained gardens, and outings."
        )
        result = {
            "facts": ["married couple", "currently independent", "Las Vegas"],
            "preferences": ["excellent food", "activities", "well maintained gardens", "outings"],
            "constraints": [],
            "concerns": ["future care security"],
            "implications": [],
            "statements": [
                {"raw_text": "married independent couple", "meaning": "couple currently independent", "importance": "CONTEXT", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["household.couple", "care.current_independence"], "clarification_question": None, "research_task": None},
                {"raw_text": "future care security", "meaning": "future care path matters", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["care.future_continuum"], "clarification_question": None, "research_task": None},
                {"raw_text": "excellent food", "meaning": "high dining quality", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["dining.quality"], "clarification_question": None, "research_task": None},
                {"raw_text": "activities", "meaning": "rich activity program", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["lifestyle.activities"], "clarification_question": None, "research_task": None},
                {"raw_text": "well maintained gardens", "meaning": "landscaped outdoor environment", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["environment.landscaping"], "clarification_question": None, "research_task": None},
                {"raw_text": "outings", "meaning": "organized external outings", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["lifestyle.outings"], "clarification_question": None, "research_task": None},
            ],
            "next_question": None,
            "research_requests": [],
            "decision_readiness": "READY",
            "statement_coverage_percent": 100.0,
            "dropped_statement_count": 0,
            "governance": {"ai_based": True, "learning_center_consulted": True},
        }
        context = self._run(query, result, {
            "budget": 8000,
            "entranceFeeTolerance": "No",
        })
        semantic = context["semantic_ai"]
        self.assertEqual("CONSULTED_AND_VALIDATED", semantic["status"])
        self.assertEqual("SEMANTIC_AI", context["interview_policy"]["owner"])
        self.assertEqual([], context["adaptive_questions"])
        statements = semantic["result"]["statements"]
        mapped = {p for s in statements for p in s["mapped_parameters"]}
        self.assertTrue({"dining.quality", "lifestyle.activities", "environment.landscaping", "lifestyle.outings", "care.future_continuum"}.issubset(mapped))
        self.assertEqual(0, semantic["result"]["dropped_statement_count"])

    def test_walker_100m_no_wheelchair_requires_compact_layout_question_before_ranking(self) -> None:
        query = "Man age 80 uses a walker, can walk only about 100 meters, refuses wheelchair use, otherwise independent, wants senior living in Las Vegas."
        question = "Would you prefer a compact community or central building where your apartment, dining, activities and main services are within short walking distances?"
        result = {
            "facts": ["80", "walker", "walking limit about 100m", "refuses wheelchair", "otherwise independent"],
            "preferences": [], "constraints": ["walking limit", "no wheelchair"], "concerns": [],
            "implications": [{"derived_from": ["walking limit about 100m", "refuses wheelchair"], "implication": "internal distances and layout may be decisive", "certainty": "LIKELY", "requires_confirmation": True}],
            "statements": [
                {"raw_text": "can walk only about 100 meters and refuses wheelchair", "meaning": "community layout may materially affect independent access", "importance": "UNKNOWN", "knowledge_state": "AMBIGUOUS", "status": "ASKED", "mapped_parameters": ["physical.compact_layout", "physical.internal_walking_distance"], "clarification_question": question, "research_task": None}
            ],
            "next_question": question,
            "research_requests": [],
            "decision_readiness": "NEEDS_CLARIFICATION",
            "statement_coverage_percent": 100.0,
            "dropped_statement_count": 0,
            "governance": {"ai_based": True, "learning_center_consulted": True},
        }
        context = self._run(query, result)
        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])
        self.assertEqual(1, len(context["adaptive_questions"]))
        self.assertTrue(context["adaptive_questions"][0]["question_key"].startswith("semantic_ai_high_information_question:"))
        self.assertIn("short walking distances", context["adaptive_questions"][0]["question"].lower())

    def test_widow_gluten_allergy_and_no_cooking_become_safety_and_meal_requirements(self) -> None:
        query = "75-year-old widow, currently independent, wants luxury, loves company and games, has a gluten allergy and does not cook."
        question = "Do you require all daily meals to be provided with a medically safe gluten-free protocol, including cross-contact controls?"
        result = {
            "facts": ["75-year-old widow", "currently independent", "does not cook"],
            "preferences": ["luxury", "company", "games"],
            "constraints": ["gluten allergy"], "concerns": [],
            "implications": [{"derived_from": ["gluten allergy", "does not cook"], "implication": "safe daily meal provision may be a MUST", "certainty": "LIKELY", "requires_confirmation": True}],
            "statements": [
                {"raw_text": "wants luxury", "meaning": "luxury environment preference", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["environment.luxury"], "clarification_question": None, "research_task": None},
                {"raw_text": "loves company and games", "meaning": "social and game programming are important", "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["lifestyle.social", "lifestyle.games"], "clarification_question": None, "research_task": None},
                {"raw_text": "gluten allergy", "meaning": "medical dietary safety constraint", "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["diet.gluten_free_safe"], "clarification_question": None, "research_task": None},
                {"raw_text": "does not cook", "meaning": "depends on community meal provision", "importance": "MUST", "knowledge_state": "AMBIGUOUS", "status": "ASKED", "mapped_parameters": ["meals.daily_provision", "diet.cross_contact_control"], "clarification_question": question, "research_task": None},
            ],
            "next_question": question,
            "research_requests": [],
            "decision_readiness": "NEEDS_CLARIFICATION",
            "statement_coverage_percent": 100.0,
            "dropped_statement_count": 0,
            "governance": {"ai_based": True, "learning_center_consulted": True},
        }
        context = self._run(query, result)
        statements = context["semantic_ai"]["result"]["statements"]
        allergy = next(s for s in statements if s["raw_text"] == "gluten allergy")
        no_cook = next(s for s in statements if s["raw_text"] == "does not cook")
        self.assertEqual("MUST", allergy["importance"])
        self.assertEqual("MUST", no_cook["importance"])
        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])
        self.assertEqual(1, len(context["adaptive_questions"]))
        self.assertIn("cross-contact", context["adaptive_questions"][0]["question"])


if __name__ == "__main__":
    unittest.main()
