from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context
from app.services.patient_decision_engine import run_patient_decision_engine


class GoldenMother90FullLifecycleTests(unittest.TestCase):
    """Golden regression for a complete client-owned clarification -> READY -> ranking journey."""

    def _base_state(self) -> dict:
        return {
            "relationship": "Mom",
            "ageGroup": "90+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "No preference"},
                "familyProfile": {"socialInteractionNeed": "Important"},
                "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
                "scoringEngine": {"adaptiveSignals": []},
            },
        }

    def _query(self) -> str:
        return (
            "My mother is 90 and we are looking across the Las Vegas Valley. She is mentally alert, "
            "has no dementia, is mobile, but needs daily help with bathing, dressing and medication. "
            "She would like a friendly social environment and we want the least restrictive safe setting."
        )

    def test_budget_question_then_ready_then_governed_top5(self) -> None:
        state = self._base_state()
        question = "What monthly housing-and-care budget would be comfortable for your mother?"
        first_ai = {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [
                {
                    "raw_text": "budget not provided",
                    "meaning": "monthly affordability is unknown",
                    "importance": "MUST",
                    "knowledge_state": "UNKNOWN",
                    "status": "ASKED",
                    "mapped_parameters": ["monthly_affordability"],
                    "clarification_question": question,
                    "research_task": None,
                }
            ],
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=first_ai
        ):
            first = build_human_intelligence_context(state, self._query())

        self.assertEqual(first["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(len(first["adaptive_questions"]), 1)
        self.assertEqual(first["adaptive_questions"][0]["question"], question)
        self.assertEqual(first["adaptive_questions"][0].get("target_fact_key"), "monthly_budget")

        answered = self._base_state()
        answered["budget"] = 8000
        answered["humanIntelligenceV2"]["scoringEngine"]["adaptiveSignals"] = [
            {
                "questionKey": first["adaptive_questions"][0]["question_key"],
                "answer": "$8,000 per month",
                "signalType": "decision-interview",
                "impactExplanation": f"Question: {question} | explicit client answer",
                "infoGain": 1,
            }
        ]
        ready_ai = {"decision_readiness": "READY", "next_question": None, "statements": [
            {
                "raw_text": "monthly budget $8,000",
                "meaning": "usable monthly affordability envelope",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "status": "USED",
                "mapped_parameters": ["monthly_affordability"],
                "clarification_question": None,
                "research_task": None,
            }
        ]}

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ready_ai
        ):
            result = run_patient_decision_engine(answered, self._query(), limit=5)

        decision = result["decision_intelligence"]
        self.assertTrue(decision["recommendation_execution_allowed"])
        self.assertEqual(result["result_count"], 5)
        self.assertGreater(result["total_candidates_scored"], 0)
        self.assertTrue(all(str(row.get("state") or "").upper() == "NV" for row in result["results"]))
        self.assertTrue(all(row.get("is_las_vegas_valley") is True for row in result["results"]))
        self.assertTrue(all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in result["results"]))
        self.assertTrue(all(row.get("canonical_type") == "ASSISTED_LIVING_RFG" for row in result["results"]))
        self.assertEqual([row["rank_position"] for row in result["results"]], [1, 2, 3, 4, 5])
        self.assertEqual(decision["human_intelligence"]["decision_readiness"], "READY")
        self.assertEqual(decision["human_intelligence"]["adaptive_questions"], [])


if __name__ == "__main__":
    unittest.main()
