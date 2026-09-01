from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.services.ai_process_owner_runtime import _phase, attach_ai_process_owner
from app.services.facility_parameter_service import get_canonical_facility_index
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context
from app.services.patient_decision_engine import run_patient_decision_engine


class GoldenMother90FullLifecycleTests(unittest.TestCase):
    """Golden regression for clarification -> MUST verification -> ranking -> AI process owner."""

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

    def test_budget_question_then_medication_verification_then_governed_top5(self) -> None:
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

        # Client intent is complete, but medication support is a facility-owned MUST.
        # Without governed evidence no candidate may be exposed as a recommendation.
        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_SEMANTIC_AI_REQUIRED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
        }, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ready_ai
        ):
            pending_result = run_patient_decision_engine(answered, self._query(), limit=5)

        pending_decision = pending_result["decision_intelligence"]
        self.assertEqual("READY", pending_decision["human_intelligence"]["decision_readiness"])
        self.assertFalse(pending_decision["recommendation_execution_allowed"])
        self.assertEqual([], pending_result["results"])
        self.assertGreater(pending_result.get("must_pending_verification_count") or 0, 0)
        self.assertTrue(
            all(
                "MEDICATION_SUPPORT_AVAILABLE" in (item.get("must_unknown") or [])
                for item in (pending_result.get("must_pending_verification_candidates") or [])
            )
        )

        # Once governed provider evidence explicitly verifies medication support, the
        # same completed client interview may proceed to ranking. This is a test
        # fixture for the downstream ranking/process-owner lifecycle, not a claim that
        # every real facility has this service.
        #
        # One mock, not two: client_intent_runtime's MUST gate and
        # combined_care_solution_runtime's medication-delivery reconciliation both read
        # governed provider evidence through the single shared
        # governed_evidence_runtime.agent_and_provider_payloads(). Before that
        # consolidation each module had its own separately-written reader
        # (_governed_provider_payloads vs _payloads); patching only one of them made
        # this scenario fail once MEDICATION_SUPPORT_AVAILABLE reconciliation was wired
        # in, because the MUST gate saw the mocked PASS while combined_care_solution's
        # independent reader saw no evidence and downgraded it back to
        # PENDING_VERIFICATION. Patching the one shared function both modules call
        # keeps this test representative of a real verified finding, which really does
        # flow through both readers identically now.
        verified_medication_payload = [{"medication_support_verified": True}]
        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_SEMANTIC_AI_REQUIRED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
        }, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ready_ai
        ), patch(
            "app.services.governed_evidence_runtime.agent_and_provider_payloads", return_value=verified_medication_payload
        ):
            result = run_patient_decision_engine(answered, self._query(), limit=5)

        decision = result["decision_intelligence"]
        # A deterministic ordering is useful internally, but it is not a completed
        # AI ranking and may not be exposed as a recommendation. Canonical decision
        # state reaches this via the AI_RANKING phase (eligible candidates exist,
        # ranking has not completed) rather than EVIDENCE_COLLECTION (no eligible
        # candidates yet) -- see test_canonical_decision_state.py's own
        # BLOCKED_AI_RANKING fixture for the same distinction.
        self.assertFalse(decision["recommendation_execution_allowed"])
        self.assertEqual(decision["recommendation_visibility"], "BLOCKED_AI_RANKING")
        self.assertEqual(result["result_count"], 0)
        self.assertGreater(result["total_candidates_scored"], 0)
        self.assertEqual(decision["human_intelligence"]["decision_readiness"], "READY")
        self.assertEqual(decision["human_intelligence"]["adaptive_questions"], [])

        expected_phase = _phase(result, answered)
        action_by_phase = {
            "CLARIFICATION": "ASK_CLIENT",
            "RESEARCH": "RESEARCH_FACILITY_FACTS",
            "COMPARE": "COMPARE_OPTIONS",
            "RECOMMEND": "PRESENT_RECOMMENDATION",
            "FOLLOW_UP": "FOLLOW_UP",
            "DISCOVERY": "ASK_CLIENT",
        }
        expected_action = action_by_phase[expected_phase]
        top_ids = [row["canonical_facility_id"] for row in result["results"]]
        process_packet = {
            "process_phase": expected_phase,
            "process_summary": "Continue the governed mother-90 decision from the current evidence state.",
            "conclusions": [{"conclusion": "The ranked options satisfy the governed care-setting gate.", "evidence_facility_ids": top_ids[:2]}],
            "proposed_solutions": [{"solution": "Advance the leading governed options without inventing missing provider facts.", "facility_ids": top_ids[:2], "why": "They passed the current MUST gate.", "verification_needed": []}],
            "next_best_action": {"action": expected_action, "reason": "Advance the next governed decision step.", "question": None, "research_tasks": []},
            "follow_up_plan": ["Preserve client answers and continue from this decision state."],
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_process_owner_runtime._default_transport", return_value=process_packet
        ):
            owned = attach_ai_process_owner(result, answered, self._query())
        owner = owned["decision_intelligence"]["process_owner"]
        self.assertEqual(owner["status"], "ACTIVE")
        self.assertEqual(owner["process_phase"], expected_phase)
        self.assertEqual(owner["next_best_action"]["action"], expected_action)

        print("MOTHER90_GOLDEN=" + json.dumps({
            "first_question": question,
            "answered_budget": 8000,
            "pre_verification_visible_results": pending_result["result_count"],
            "pending_medication_candidates": pending_result.get("must_pending_verification_count"),
            "decision_readiness": decision["human_intelligence"]["decision_readiness"],
            "result_count_after_medication_evidence": result["result_count"],
            "top5": [
                {
                    "rank": row["rank_position"],
                    "facility_name": row.get("facility_name"),
                    "city": row.get("city"),
                    "canonical_type": row.get("canonical_type"),
                    "hard_gate": (row.get("client_intent_fit") or {}).get("hard_gate"),
                    "must_pass": (row.get("client_intent_fit") or {}).get("must_pass"),
                }
                for row in result["results"]
            ],
            "process_phase": owner["process_phase"],
            "next_best_action": owner["next_best_action"]["action"],
        }, indent=2))


if __name__ == "__main__":
    unittest.main()
