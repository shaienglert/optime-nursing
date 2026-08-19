from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.facility_parameter_service import get_canonical_facility_index, refresh_runtime_cache
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.provider_housing_runtime import attach_provider_housing_evidence, get_provider_housing_evidence
from app.services.public_reputation_runtime import get_public_reputation


class ProviderHousingRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("provider_housing_test_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("provider_housing_test_teardown")

    def test_las_ventanas_provider_evidence_attaches_without_snf_lifestyle_duplication(self) -> None:
        index = get_canonical_facility_index()
        candidates = [
            dict(row, canonical_facility_id=canonical_id)
            for canonical_id, row in index.items()
            if canonical_id in {"NV-LIC-4000-AGC-31", "NV-LIC-4529-SNF-31"}
        ]
        self.assertEqual(len(candidates), 2)
        attach_provider_housing_evidence(candidates)
        by_type = {str(row.get("canonical_type")): row for row in candidates}
        assisted = by_type["ASSISTED_LIVING_RFG"]
        snf = by_type["SKILLED_NURSING"]

        self.assertIn("INDEPENDENT_LIVING", assisted.get("housing_modalities") or [])
        self.assertIn("LIFE_PLAN_CCRC", assisted.get("housing_modalities") or [])
        evidence = (assisted.get("provider_housing_evidence") or {}).get("evidence") or {}
        self.assertTrue(evidence.get("couple_coresidence_verified"))
        self.assertTrue(evidence.get("outside_care_allowed_verified"))
        self.assertTrue(evidence.get("rehab_verified"))
        self.assertTrue(evidence.get("social_engagement_verified"))
        self.assertEqual(assisted.get("facility_name"), "Las Ventanas at Summerlin")
        self.assertTrue(assisted.get("licensed_facility_name"))

        self.assertIn("LIFE_PLAN_CCRC", snf.get("housing_modalities") or [])
        self.assertIsNone(snf.get("provider_housing_evidence"))
        self.assertTrue(snf.get("life_plan_primary_evidence"))

    def test_provider_identity_can_resolve_exact_address_with_governed_market(self) -> None:
        row = {
            "facility_name": "LEGACY LICENSE NAME",
            "address": "2000 N Rampart Blvd",
            "city": "Las Vegas",
            "state": "NV",
            "canonical_type": "ASSISTED_LIVING_RFG",
        }
        evidence = get_provider_housing_evidence(row)
        self.assertTrue(evidence["matched"])
        self.assertEqual((evidence.get("provider_housing_evidence") or {}).get("community_name"), "Atria Seville")

    def test_independent_living_unknown_adl_is_not_hard_failed(self) -> None:
        state = {
            "relationship": "Dad",
            "ageGroup": "80+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "Large community"},
                "familyProfile": {"socialInteractionNeed": "Very important"},
            },
        }
        query = (
            "A couple age 80+ wants to move to senior living in Las Vegas with culture and classes. "
            "The husband had spinal surgery and needs rehabilitation and temporary help with bathing and dressing for 3 months. "
            "The wife is independent and they want to live together."
        )
        strategy = build_living_strategy_context(state, query)
        human = build_human_intelligence_context(questionnaire_state=state, natural_language_query=query)
        human["living_strategy"] = strategy
        intent = build_client_intent(state, query, strategy, human)
        row = {
            "facility_name": "Unknown IL",
            "address": "1 Test St",
            "city": "LAS VEGAS",
            "state": "NV",
            "canonical_type": "INDEPENDENT_LIVING",
            "housing_modalities": ["INDEPENDENT_LIVING"],
            "matched_needs": [],
            "unknown_critical_needs": [],
        }
        fit = evaluate_candidate_intent(row, intent)
        self.assertNotEqual(fit["hard_gate"], "FAIL")
        self.assertIn("ADL_SUPPORT_AVAILABLE", fit["must_unknown"])

    def test_las_ventanas_primary_evidence_satisfies_couple_rehab_musts(self) -> None:
        state = {
            "relationship": "Wife",
            "ageGroup": "80+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "Large community"},
                "familyProfile": {"socialInteractionNeed": "Very important"},
            },
        }
        query = (
            "My husband and I are both over 80 and want to move to senior living in Las Vegas with lots of culture, classes and activities. "
            "My husband had spinal surgery and needs rehabilitation. He is expected to return to walking, but for the next 3 months he needs help with bathing and dressing. "
            "I am independent and we want to live together."
        )
        strategy = build_living_strategy_context(state, query)
        human = build_human_intelligence_context(questionnaire_state=state, natural_language_query=query)
        human["living_strategy"] = strategy
        intent = build_client_intent(state, query, strategy, human)

        index = get_canonical_facility_index()
        row = dict(index["NV-LIC-4000-AGC-31"], canonical_facility_id="NV-LIC-4000-AGC-31")
        row["matched_needs"] = []
        row["unknown_critical_needs"] = []
        attach_provider_housing_evidence([row])
        fit = evaluate_candidate_intent(row, intent)

        self.assertEqual(fit["hard_gate"], "PASS")
        for key in ("LAS_VEGAS", "COUPLE_CORESIDENCE", "ADL_SUPPORT_AVAILABLE", "REHAB_PATH_AVAILABLE", "RECOVERY_TRANSITION_COMPATIBLE", "NO_FORCED_MEMORY_PLACEMENT"):
            self.assertIn(key, fit["must_pass"])
        self.assertIn("RICH_CULTURE_AND_ACTIVITIES", fit["nice_match"])

    def test_reputation_is_identity_scoped_and_secondary_to_fit(self) -> None:
        exact = get_public_reputation({"facility_name": "Oakey Assisted Living", "address": "3900 W Oakey Blvd", "city": "Las Vegas"})
        self.assertTrue(exact["identity_verified"])
        self.assertEqual(exact["rating"], 4.3)
        self.assertEqual(exact["review_count"], 46)
        alias = get_public_reputation({
            "facility_name": "LAS VENTANAS RETIREMENT COMM",
            "aliases": ["Las Ventanas at Summerlin"],
            "address": "10401 W Charleston Blvd",
            "city": "Las Vegas",
        })
        self.assertTrue(alias["identity_verified"])
        self.assertEqual(alias["rating"], 2.8)
        mismatch = get_public_reputation({"facility_name": "Oakey Assisted Living", "address": "3901 W Oakey Blvd", "city": "Las Vegas"})
        self.assertFalse(mismatch["identity_verified"])
        self.assertEqual(mismatch["rating"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
