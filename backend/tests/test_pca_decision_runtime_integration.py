from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine
from app.services.personal_care_agency_runtime import load_personal_care_agency_evidence


class PCADecisionRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("pca_decision_integration_setup")
        load_personal_care_agency_evidence.cache_clear()

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("pca_decision_integration_teardown")
        load_personal_care_agency_evidence.cache_clear()

    def _run_ready(self, state: dict, query: str, limit: int) -> dict:
        # PCA tests start after interview completion; resolve any rank-sensitive
        # environment preference explicitly instead of bypassing the Guardian.
        hi = state.setdefault("humanIntelligenceV2", {})
        hi.setdefault("personalityProfile", {}).setdefault("communitySizePreference", "No preference")
        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(
            os.environ,
            {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"},
            clear=False,
        ), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
            return_value=ai_result,
        ):
            result = run_patient_decision_engine(state, query, limit=limit)
        self.assertTrue(result["decision_intelligence"]["recommendation_execution_allowed"])
        return result

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
        result = self._run_ready(state, query, limit=10)
        layer = result["decision_intelligence"]["care_partner_layer"]
        evidence = load_personal_care_agency_evidence()
        self.assertEqual(layer["licensed_valley_universe_count"], 363)
        self.assertEqual(layer["operationally_verified_count"], len(evidence["records"]))
        self.assertEqual(layer["status"], "CANDIDATES_PENDING_OPERATIONAL_VERIFICATION")
        self.assertIn("BATHING_ASSISTANCE", layer["requirements"]["required_services"])
        self.assertIn("DRESSING_ASSISTANCE", layer["requirements"]["required_services"])

        options = layer["candidate_options"]
        self.assertGreaterEqual(len(options), 2)
        self.assertEqual(result["care_partner_options"], options)

        live_evidence_by_license = {row["license_number"]: row for row in evidence["records"]}
        surfaced_licenses = {row["license_number"] for row in options}
        self.assertTrue(surfaced_licenses.issubset(set(live_evidence_by_license)))
        self.assertTrue(all(row["license_status"] == "ACTIVE" for row in options))
        self.assertTrue(all(row["bathing_assistance"] is not False for row in options))
        self.assertTrue(all(row["dressing_assistance"] is not False for row in options))
        self.assertTrue(all((row.get("care_agency_fit") or {}).get("hard_gate") != "FAIL" for row in options))

        for row in options:
            fit = row.get("care_agency_fit") or {}
            matched = set(fit.get("matched") or [])
            unknowns = set(fit.get("material_unknowns") or [])
            if row["bathing_assistance"] is True:
                self.assertIn("BATHING_ASSISTANCE", matched)
            else:
                self.assertIn("BATHING_ASSISTANCE", unknowns)
            if row["dressing_assistance"] is True:
                self.assertIn("DRESSING_ASSISTANCE", matched)
            else:
                self.assertIn("DRESSING_ASSISTANCE", unknowns)

        self.assertTrue(all(row["hourly_rate"] == "UNKNOWN" for row in options))

        # Brand names are not acceptance criteria. A live, identity-verified provider
        # may rank outside Top-N when more operational facts remain UNKNOWN.
        self.assertIn("9703-PCS-7", live_evidence_by_license)
        self.assertEqual(live_evidence_by_license["9703-PCS-7"]["agency_name"], "RIGHT AT HOME LAS VEGAS")

        evidence_by_id = {row["agency_id"]: row for row in evidence["records"]}
        self.assertEqual(evidence_by_id["NV-PCA-11759-PCS-1"]["minimum_billable_hours"], 0)
        self.assertEqual(evidence_by_id["NV-PCA-7836-PCS-13"]["minimum_billable_hours"], 4)
        self.assertEqual(evidence_by_id["NV-PCA-7836-PCS-13"]["minimum_hours_policy"], "FOUR_HOURS_PER_DAY")

        homewatch = next((row for row in options if row["agency_id"] == "NV-PCA-11759-PCS-1"), None)
        if homewatch is not None:
            self.assertEqual(homewatch["minimum_billable_hours"], 0)
        amada = next((row for row in options if row["agency_id"] == "NV-PCA-7836-PCS-13"), None)
        if amada is not None:
            self.assertEqual(amada["minimum_billable_hours"], 4)

    def test_non_il_strategy_does_not_inject_pca_candidates(self) -> None:
        state = {
            "relationship": "Dad",
            "ageGroup": "80+",
            "assistanceLevel": "Needs 24/7 skilled nursing",
            "memoryStatus": "No",
        }
        result = self._run_ready(
            state,
            "My father needs 24/7 skilled nursing in Las Vegas and is not looking for independent living.",
            limit=5,
        )
        layer = result["decision_intelligence"]["care_partner_layer"]
        self.assertEqual(layer["status"], "NOT_APPLICABLE")
        self.assertEqual(result["care_partner_options"], [])


if __name__ == "__main__":
    unittest.main()
