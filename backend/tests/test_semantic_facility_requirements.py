from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.semantic_intent_ai import interpret_client_intent_with_ai
from app.services.semantic_facility_requirements import apply_semantic_facility_requirements, extract_semantic_facility_requirements


class SemanticFacilityRequirementTests(unittest.TestCase):
    def test_facility_research_does_not_deadlock_client_readiness(self) -> None:
        ai = {
            "facts": ["independent resident"],
            "preferences": [],
            "constraints": ["100 meter route"],
            "concerns": [],
            "implications": [],
            "statements": [
                {
                    "raw_text": "services must be within 100 meters",
                    "meaning": "actual unit route distance is a hard requirement",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "RESEARCH_REQUIRED",
                    "mapped_parameters": ["unit_to_dining_distance", "internal_route_distance"],
                    "clarification_question": None,
                    "research_task": "verify actual route distance for each available unit",
                }
            ],
            "next_question": None,
            "research_requests": ["verify route distance"],
            "decision_readiness": "NEEDS_RESEARCH",
        }
        learning = {"advisor": "OPTIME_NURSING_LEARNING_CENTER", "consulted": True, "agent_count": 1, "available_agent_count": 1, "agents": [], "policy": {}}
        with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value=learning):
            result = interpret_client_intent_with_ai(user_text="100 meter route", questionnaire_state={}, transport=lambda _: ai)
        self.assertEqual("READY", result["decision_readiness"])
        self.assertEqual("CLIENT_INTENT_COMPLETE_FACILITY_RESEARCH_DEFERRED", result["readiness_normalization"]["reason"])
        self.assertEqual("RESEARCH_REQUIRED", result["statements"][0]["status"])

    def test_semantic_mobility_and_dietary_musts_survive_to_facility_gate(self) -> None:
        payload = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [
                                {
                                    "raw_text": "within 100 meters",
                                    "meaning": "short internal route required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["unit_to_dining_distance", "layout_fit"],
                                    "research_task": "verify route",
                                },
                                {
                                    "raw_text": "safe gluten-free with cross-contact controls",
                                    "meaning": "medical dietary safety required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["gluten_free_meals_required", "cross_contact_controls_required"],
                                    "research_task": "verify cross-contact controls",
                                },
                                {
                                    "raw_text": "all daily meals",
                                    "meaning": "all meals required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["all_daily_meals_required"],
                                    "research_task": "verify meal plan",
                                },
                            ]
                        }
                    }
                }
            }
        }
        rows = extract_semantic_facility_requirements(payload)
        self.assertEqual({"SEMANTIC_MOBILITY_LAYOUT", "SEMANTIC_DIETARY_SAFETY", "SEMANTIC_ALL_DAILY_MEALS"}, {row["key"] for row in rows})

    def test_ambiguous_client_owned_value_is_not_promoted_to_facility_must(self) -> None:
        payload = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [{
                                "raw_text": "budget 8000",
                                "meaning": "period unknown",
                                "importance": "MUST",
                                "knowledge_state": "AMBIGUOUS",
                                "status": "RESEARCH_REQUIRED",
                                "mapped_parameters": ["budget_period"],
                                "research_task": "verify budget period",
                            }]
                        }
                    }
                }
            }
        }
        self.assertEqual([], extract_semantic_facility_requirements(payload))

    def test_stamped_false_agent_evidence_never_hard_fails_a_semantic_must(self) -> None:
        # decision_research_worker.py stamps social_engagement_verified=False by default
        # on every research record, regardless of which dimension was actually
        # requested -- so a facility with unrelated agent research (e.g. a
        # couple_coresidence check) must not be excluded from a client's social-
        # engagement MUST just because that unrelated record carries the default False.
        result = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [{
                                "raw_text": "organized activities and card games so she never feels isolated",
                                "meaning": "material social programming required",
                                "importance": "MUST",
                                "knowledge_state": "KNOWN",
                                "status": "RESEARCH_REQUIRED",
                                "mapped_parameters": ["organized_activities", "isolation"],
                                "research_task": "verify organized social programming",
                            }]
                        }
                    }
                }
            },
            "results": [
                {
                    "canonical_facility_id": "TEST-1",
                    "facility_name": "Test Facility",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "agent_person_fit_evidence": [
                        {"payload": {"dimension": "couple_coresidence", "social_engagement_verified": False, "couple_coresidence_verified": True}}
                    ],
                }
            ],
        }
        out = apply_semantic_facility_requirements(result)
        fit = out["results"][0]["client_intent_fit"]
        self.assertNotIn("SEMANTIC_SOCIAL_DELIVERY", fit["must_fail"])
        self.assertNotEqual("FAIL", fit["hard_gate"])
        self.assertIn("SEMANTIC_SOCIAL_DELIVERY", fit["must_unknown"])


if __name__ == "__main__":
    unittest.main()
