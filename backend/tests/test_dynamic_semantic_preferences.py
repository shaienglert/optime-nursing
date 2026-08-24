from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.semantic_preference_runtime import (
    build_dynamic_preference_model,
    build_facility_claim_ledger,
    verify_dynamic_preferences,
)


class DynamicSemanticPreferenceTests(unittest.TestCase):
    def _human(self):
        return {
            "semantic_ai": {
                "result": {
                    "preferences": [
                        "She wants a serious bridge club with regular games",
                        "She values access to gardening and outdoor horticulture",
                    ],
                    "statements": [
                        {
                            "raw_text": "Hebrew-speaking staff would make her feel at home",
                            "meaning": "Access to Hebrew-speaking staff",
                            "importance": "NICE",
                            "knowledge_state": "KNOWN",
                            "status": "USED",
                        },
                        {
                            "raw_text": "She needs medication management",
                            "meaning": "Medication management",
                            "importance": "MUST",
                            "knowledge_state": "KNOWN",
                            "status": "USED",
                        },
                    ],
                }
            }
        }

    def _row(self):
        return {
            "canonical_facility_id": "FAC-1",
            "facility_name": "Example Community",
            "canonical_type": "ASSISTED_LIVING_RFG",
            "housing_modalities": ["ASSISTED_LIVING"],
            "care_setting_fit": {"status": "PRIMARY_FIT"},
            "provider_housing_evidence": {
                "evidence": {
                    "bridge_club_schedule": "Duplicate bridge Tuesdays and Fridays",
                    "garden_program": "Resident gardening group and raised beds",
                }
            },
            # Simulates a future evidence namespace added by another research worker.
            # The preference engine must ingest it without a code change.
            "future_research_evidence_v99": {
                "observatory_outings": "Monthly dark-sky astronomy outing documented by provider calendar"
            },
            "client_intent_fit": {"public_reputation": {}},
        }

    def test_arbitrary_preferences_become_dynamic_dimensions_without_catalog(self):
        model = build_dynamic_preference_model(self._human())
        meanings = {row["semantic_meaning"] for row in model["preferences"]}
        self.assertEqual(model["preference_count"], 3)
        self.assertIn("She wants a serious bridge club with regular games", meanings)
        self.assertIn("She values access to gardening and outdoor horticulture", meanings)
        self.assertIn("Access to Hebrew-speaking staff", meanings)
        self.assertTrue(model["hard_coded_preference_catalog_forbidden"])
        self.assertEqual(len({row["preference_id"] for row in model["preferences"]}), 3)

    def test_claim_ledger_is_generic_and_accepts_future_evidence_namespaces(self):
        ledger = build_facility_claim_ledger(self._row())
        paths = {claim["path"] for claim in ledger["claims"]}
        self.assertTrue(any("bridge_club_schedule" in path for path in paths))
        self.assertTrue(any("garden_program" in path for path in paths))
        self.assertTrue(any("future_research_evidence_v99.observatory_outings" in path for path in paths))
        self.assertEqual(ledger["source_model"], "COMPLETE_GOVERNED_CANDIDATE_RECORD")

    def test_ai_cannot_assert_match_without_governed_claim(self):
        model = build_dynamic_preference_model({"semantic_ai": {"result": {"preferences": ["A quiet astronomy club"], "statements": []}}})
        row = self._row()
        bad_packet = {
            "assessments": [
                {
                    "preference_id": model["preferences"][0]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [],
                    "reason": "sounds plausible",
                    "provider_question_if_unknown": None,
                }
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=bad_packet
        ):
            with self.assertRaisesRegex(RuntimeError, "AI_PREFERENCE_VERIFICATION_REQUIRED_FAILED"):
                verify_dynamic_preferences([row], model)

    def test_arbitrary_preferences_can_match_only_by_citing_existing_claims(self):
        human = {"semantic_ai": {"result": {"preferences": ["Regular bridge games", "Resident gardening"], "statements": []}}}
        model = build_dynamic_preference_model(human)
        row = self._row()
        ledger = build_facility_claim_ledger(row)
        bridge_claim = next(c["claim_id"] for c in ledger["claims"] if "bridge_club_schedule" in c["path"])
        garden_claim = next(c["claim_id"] for c in ledger["claims"] if "garden_program" in c["path"])
        packet = {
            "assessments": [
                {
                    "preference_id": model["preferences"][0]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [bridge_claim],
                    "reason": "The governed schedule explicitly documents regular bridge games.",
                    "provider_question_if_unknown": None,
                },
                {
                    "preference_id": model["preferences"][1]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [garden_claim],
                    "reason": "The governed evidence explicitly documents resident gardening.",
                    "provider_question_if_unknown": None,
                },
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=packet
        ):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_COMPLETE")
        self.assertEqual(summary["nice_complete_candidate_count"], 1)

    def test_missing_evidence_stays_unknown_not_negative(self):
        model = build_dynamic_preference_model({"semantic_ai": {"result": {"preferences": ["Weekly astronomy lectures"], "statements": []}}})
        row = self._row()
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "0"}, clear=False):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_UNVERIFIED")
        self.assertEqual(row["dynamic_preference_fit"]["assessments"][0]["status"], "UNKNOWN")
        self.assertEqual(summary["verification_required_count"], 1)


if __name__ == "__main__":
    unittest.main()
