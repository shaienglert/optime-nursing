from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

from app.services.ai_process_owner_runtime import attach_ai_process_owner


class AIProcessOwnerRuntimeTests(unittest.TestCase):
    def _result(self):
        return {
            "results": [
                {
                    "canonical_facility_id": "FAC-1",
                    "facility_name": "Facility One",
                    "canonical_type": "INDEPENDENT_LIVING",
                    "housing_modalities": ["INDEPENDENT_LIVING"],
                    "rank_position": 1,
                    "care_setting_fit": {"status": "PRIMARY_FIT"},
                    "client_intent_fit": {
                        "hard_gate": "PASS",
                        "must_pass": ["LAS_VEGAS"],
                        "must_unknown": [],
                        "must_fail": [],
                        "nice_match": ["COMMUNITY_ENVIRONMENT_MATCH"],
                        "public_reputation": {},
                    },
                    "combined_care_solution": {},
                    "care_partner_access": {},
                    "regulatory_history": {},
                },
                {
                    "canonical_facility_id": "FAC-2",
                    "facility_name": "Facility Two",
                    "canonical_type": "LIFE_PLAN_CCRC",
                    "housing_modalities": ["LIFE_PLAN_CCRC", "INDEPENDENT_LIVING"],
                    "rank_position": 2,
                    "care_setting_fit": {"status": "POSSIBLE_FIT"},
                    "client_intent_fit": {
                        "hard_gate": "PASS",
                        "must_pass": ["LAS_VEGAS"],
                        "must_unknown": [],
                        "must_fail": [],
                        "nice_match": [],
                        "public_reputation": {},
                    },
                    "combined_care_solution": {},
                    "care_partner_access": {},
                    "regulatory_history": {},
                },
            ],
            "patient_needs_profile": {
                "needs": [],
                "location_city": "LAS VEGAS",
                "living_strategy": {},
                "client_intent": {},
            },
            "decision_intelligence": {
                "recommendation_execution_allowed": True,
                "decision_finality": "FINAL",
                "human_intelligence": {"decision_readiness": "READY"},
                "strategy_universe": {"status": "SUFFICIENT_FOR_LEADING_STRATEGIES"},
                "care_partner_layer": {},
                "must_gate": {"eligible": 2, "pending_verification": 0, "rejected": 0, "selected_must_unknown_count": 0},
                "facility_selection_pipeline": {
                    "ai_ranking": {"status": "AI_BATCH_RANKED"},
                    "dynamic_preferences": {"preference_count": 0, "nice_complete_candidate_count": 0, "verification_required_count": 0},
                },
                "ranking_order": ["CLIENT_INTENT", "MUST_GATE", "NICE_TO_HAVE"],
            },
        }

    def _packet(self, *, phase="COMPARE", action="PRESENT_RECOMMENDATION"):
        return {
            "process_phase": phase,
            "process_summary": "Two governed options remain.",
            "conclusions": [
                {"conclusion": "Facility One is the stronger care-setting fit.", "evidence_facility_ids": ["FAC-1"]}
            ],
            "proposed_solutions": [
                {"solution": "Present Facility One as the leading option.", "facility_ids": ["FAC-1"], "why": "Primary fit and MUST pass.", "verification_needed": []}
            ],
            "next_best_action": {
                "action": action,
                "reason": "Client intent and governed evidence determine the next step.",
                "question": None,
                "research_tasks": [],
            },
            "follow_up_plan": ["Confirm client reaction and revisit if priorities change."],
        }

    def test_process_owner_uses_only_governed_candidates_and_selects_next_action(self):
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", return_value=self._packet()
        ):
            result = attach_ai_process_owner(self._result(), {}, "Find the best option")
        owner = result["decision_intelligence"]["process_owner"]
        self.assertEqual(owner["status"], "ACTIVE")
        self.assertEqual(owner["owner"], "SEMANTIC_AI_PROCESS_OWNER")
        self.assertEqual(owner["process_phase"], "COMPARE")
        self.assertEqual(owner["next_best_action"]["action"], "PRESENT_RECOMMENDATION")
        self.assertTrue(owner["governance"]["candidate_identity_closed_world"])
        self.assertEqual(owner["governance"]["expected_phase"], "COMPARE")
        self.assertTrue(result["decision_intelligence"]["recommendation_execution_allowed"])

    def test_process_owner_continues_to_follow_up_after_compare_return(self):
        questionnaire_state = {
            "aiProcessContinuity": {
                "phase": "FOLLOW_UP",
                "lastEvent": "COMPARE_RETURNED",
                "shortlistFacilityIds": ["FAC-1", "FAC-2"],
                "comparedFacilityIds": ["FAC-1", "FAC-2"],
                "updatedAt": "2026-08-23T10:00:00Z",
            }
        }
        ai_packet = {
            "process_phase": "FOLLOW_UP",
            "process_summary": "The client has compared both finalists.",
            "conclusions": [
                {"conclusion": "The remaining choice is between primary fit and continuum flexibility.", "evidence_facility_ids": ["FAC-1", "FAC-2"]}
            ],
            "proposed_solutions": [
                {"solution": "Resolve the final trade-off before committing.", "facility_ids": ["FAC-1", "FAC-2"], "why": "Both finalists passed MUST gates.", "verification_needed": []}
            ],
            "next_best_action": {
                "action": "FOLLOW_UP",
                "reason": "The comparison is complete; continue from the client's shortlist rather than restarting discovery.",
                "question": "Which trade-off matters more after seeing them side by side?",
                "research_tasks": [],
            },
            "follow_up_plan": ["Record the client's final preference and verify any remaining provider-specific unknowns."],
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", return_value=ai_packet
        ):
            result = attach_ai_process_owner(self._result(), questionnaire_state, "Continue my decision")
        owner = result["decision_intelligence"]["process_owner"]
        self.assertEqual(owner["status"], "ACTIVE")
        self.assertEqual(owner["process_phase"], "FOLLOW_UP")
        self.assertEqual(owner["governance"]["expected_phase"], "FOLLOW_UP")
        self.assertEqual(owner["next_best_action"]["action"], "FOLLOW_UP")
        self.assertEqual(owner["prior_process_state"]["lastEvent"], "COMPARE_RETURNED")
        self.assertEqual(owner["prior_process_state"]["shortlistFacilityIds"], ["FAC-1", "FAC-2"])

    def test_process_owner_rejects_invented_facility_identity(self):
        ai_packet = self._packet()
        ai_packet["process_summary"] = "Invented option."
        ai_packet["proposed_solutions"] = [
            {"solution": "Use another facility.", "facility_ids": ["FAKE-999"], "why": "Unsupported", "verification_needed": []}
        ]
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", return_value=ai_packet
        ):
            result = attach_ai_process_owner(self._result(), {}, "Find the best option")
        owner = result["decision_intelligence"]["process_owner"]
        self.assertEqual(owner["status"], "FAILED")
        self.assertIn("UNGOVERNED_FACILITY_IDS", owner["error"])
        self.assertFalse(result["decision_intelligence"]["recommendation_execution_allowed"])

    def test_process_owner_rejects_final_recommendation_when_decision_is_provisional_or_must_unknown(self):
        provisional = copy.deepcopy(self._result())
        provisional["decision_intelligence"]["decision_finality"] = "PROVISIONAL_PENDING_PROVIDER_VERIFICATION"
        provisional["decision_intelligence"]["must_gate"]["selected_must_unknown_count"] = 1
        provisional["results"][0]["client_intent_fit"]["must_unknown"] = ["CURRENT_PRICE"]
        ai_packet = self._packet(phase="RESEARCH", action="PRESENT_RECOMMENDATION")
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", return_value=ai_packet
        ):
            result = attach_ai_process_owner(provisional, {}, "Find the best option")
        owner = result["decision_intelligence"]["process_owner"]
        self.assertEqual(owner["status"], "FAILED")
        self.assertIn("PREMATURE_RECOMMENDATION", owner["error"])
        self.assertFalse(result["decision_intelligence"]["recommendation_execution_allowed"])

    def test_required_process_owner_failure_blocks_recommendation(self):
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", side_effect=RuntimeError("AI unavailable")
        ):
            result = attach_ai_process_owner(self._result(), {}, "Find the best option")
        self.assertEqual(result["decision_intelligence"]["process_owner"]["status"], "FAILED")
        self.assertFalse(result["decision_intelligence"]["recommendation_execution_allowed"])


if __name__ == "__main__":
    unittest.main()
