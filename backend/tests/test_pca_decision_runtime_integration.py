from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine


class PCADecisionRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("pca_decision_integration_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("pca_decision_integration_teardown")

    def test_post_spine_recovery_il_strategy_surfaces_governed_pca_candidates(self) -> None:
        state = {
            "relationship": "Wife",
            "ageGroup": "80+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "familyProfile": {"socialInteractionNeed": "Very important"},
            },
        }
        query = (
            "My husband and I are both over 80 and want independent senior living in Las Vegas. "
            "He had spinal surgery and is expected to recover, but for about 3 months he needs help "
            "with getting into the shower, bathing, dressing, socks and shoes. I am independent and "
            "we want to live together."
        )
        result = run_patient_decision_engine(state, query, limit=10)
        layer = result["decision_intelligence"]["care_partner_layer"]
        self.assertEqual(layer["licensed_valley_universe_count"], 363)
        self.assertEqual(layer["operationally_verified_count"], 3)
        self.assertEqual(layer["status"], "CANDIDATES_PENDING_OPERATIONAL_VERIFICATION")
        self.assertIn("BATHING_ASSISTANCE", layer["requirements"]["required_services"])
        self.assertIn("DRESSING_ASSISTANCE", layer["requirements"]["required_services"])
        options = layer["candidate_options"]
        self.assertGreaterEqual(len(options), 2)
        names = {row["agency_name"] for row in options}
        self.assertIn("RIGHT AT HOME LAS VEGAS", names)
        self.assertIn("COMFORT KEEPERS", names)
        self.assertEqual(result["care_partner_options"], options)
        self.assertTrue(all(row["minimum_billable_hours"] == "UNKNOWN" for row in options))
        self.assertTrue(all(row["hourly_rate"] == "UNKNOWN" for row in options))

    def test_non_il_strategy_does_not_inject_pca_candidates(self) -> None:
        state = {
            "relationship": "Dad",
            "ageGroup": "80+",
            "assistanceLevel": "Needs 24/7 skilled nursing",
            "memoryStatus": "No",
        }
        result = run_patient_decision_engine(
            state,
            "My father needs 24/7 skilled nursing in Las Vegas and is not looking for independent living.",
            limit=5,
        )
        layer = result["decision_intelligence"]["care_partner_layer"]
        self.assertEqual(layer["status"], "NOT_APPLICABLE")
        self.assertEqual(result["care_partner_options"], [])


if __name__ == "__main__":
    unittest.main()
