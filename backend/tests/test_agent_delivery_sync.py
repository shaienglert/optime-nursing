import unittest
from unittest.mock import patch

from app.services import decision_governance_runtime as runtime


class AgentDeliverySyncTests(unittest.TestCase):
    def _core(self):
        return {
            "patient_needs_profile": {
                "needs": [
                    {"parameter_id": "adl_support"},
                    {"parameter_id": "pt"},
                    {"parameter_id": "activities"},
                ]
            },
            "decision_intelligence": {
                "agent_evidence_bridge": {"status": "MATERIAL_EVIDENCE_AVAILABLE"}
            },
        }

    def _row(self):
        return {
            "canonical_facility_id": "NV-LIC-4000-AGC-31",
            "client_intent_fit": {
                "nice_match": ["RICH_CULTURE_AND_ACTIVITIES"],
                "nice_unknown": [],
                "public_reputation": {
                    "identity_verified": True,
                    "rating": 2.8,
                    "review_count": 30,
                },
            },
            "agent_person_fit_evidence": [
                {"agent_key": "provider_intelligence", "confidence": 0.82},
                {"agent_key": "activities_intelligence", "confidence": 0.82},
            ],
        }

    @patch.object(runtime, "_regulatory_delivery")
    def test_every_agent_has_explicit_delivery_decision(self, regulatory):
        regulatory.return_value = {
            "applicable": True,
            "verified": [{"parameter_id": "inspection_rating", "value": 4, "source": "CMS"}],
            "unknown": ["deficiency_count"],
            "identity_source": "Nevada HCQC / ALiS",
        }
        context = {
            "knowledge_fabric": {"eligible_count": 0},
            "outcome_learning": {"sample_size": 0},
        }
        decisions = runtime._usage_decisions(self._core(), self._row(), context)
        self.assertEqual(set(decisions), set(runtime._ACTIVE_MARKET_AGENTS) | {runtime._REGULATORY_AGENT})
        self.assertTrue(all(item["decision"] in {"USED", "NOT_APPLICABLE"} for item in decisions.values()))
        self.assertEqual(decisions["regulatory_intelligence"]["decision"], "USED")
        self.assertEqual(decisions["regulatory_intelligence"]["verification"], "VERIFIED")
        self.assertEqual(decisions["outcome_learning"]["decision"], "NOT_APPLICABLE")
        self.assertEqual(decisions["nutrition_intelligence"]["decision"], "NOT_APPLICABLE")

    @patch.object(runtime, "_regulatory_delivery")
    def test_regulatory_unknown_is_delivery_not_failure(self, regulatory):
        regulatory.return_value = {
            "applicable": True,
            "verified": [],
            "unknown": list(runtime._REGULATORY_PARAMETERS),
            "identity_source": "Nevada HCQC / ALiS",
        }
        context = {
            "knowledge_fabric": {"eligible_count": 0},
            "outcome_learning": {"sample_size": 0},
        }
        decisions = runtime._usage_decisions(self._core(), self._row(), context)
        result = decisions["regulatory_intelligence"]
        self.assertEqual(result["decision"], "USED")
        self.assertEqual(result["verification"], "UNKNOWN_PRESERVED")
        self.assertIn("remain UNKNOWN", result["reason"])


if __name__ == "__main__":
    unittest.main()
