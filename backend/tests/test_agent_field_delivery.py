from __future__ import annotations

import unittest

from app.services.decision_research_worker import _apply_verified_registry_evidence


class AgentFieldDeliveryTests(unittest.TestCase):
    def test_las_ventanas_verified_provider_evidence_reaches_agent_payload(self) -> None:
        research = {
            "official_identity_verified": False,
            "social_engagement_verified": False,
            "adl_support_verified": False,
            "transportation_verified": False,
            "rehab_verified": False,
            "pt_ot_verified": False,
            "couple_coresidence_verified": False,
            "outside_care_allowed_verified": False,
            "continuum_of_care_verified": False,
            "public_rating": "UNKNOWN",
            "public_review_count": "UNKNOWN",
            "public_reputation_source": "UNKNOWN",
        }
        _apply_verified_registry_evidence(research, "NV-LIC-4000-AGC-31", "rehab_path")
        self.assertTrue(research["official_identity_verified"])
        self.assertTrue(research["adl_support_verified"])
        self.assertTrue(research["social_engagement_verified"])
        self.assertTrue(research["transportation_verified"])
        self.assertTrue(research["rehab_verified"])
        self.assertTrue(research["pt_ot_verified"])
        self.assertTrue(research["couple_coresidence_verified"])
        self.assertTrue(research["outside_care_allowed_verified"])
        self.assertTrue(research["continuum_of_care_verified"])
        self.assertEqual(research["public_rating"], 2.8)
        self.assertEqual(research["public_review_count"], 30)
        self.assertTrue(research["public_reputation_identity_verified"])

    def test_revel_verified_social_and_reputation_reach_agent_payload_without_inventing_care(self) -> None:
        research = {
            "official_identity_verified": False,
            "social_engagement_verified": False,
            "adl_support_verified": False,
            "transportation_verified": False,
            "rehab_verified": False,
            "pt_ot_verified": False,
            "couple_coresidence_verified": False,
            "outside_care_allowed_verified": False,
            "continuum_of_care_verified": False,
            "public_rating": "UNKNOWN",
            "public_review_count": "UNKNOWN",
            "public_reputation_source": "UNKNOWN",
        }
        _apply_verified_registry_evidence(research, "NV-PROVIDER-IL-REVEL-VEGAS", "social_engagement")
        self.assertTrue(research["official_identity_verified"])
        self.assertTrue(research["social_engagement_verified"])
        self.assertTrue(research["transportation_verified"])
        self.assertFalse(research["adl_support_verified"])
        self.assertFalse(research["rehab_verified"])
        self.assertEqual(research["public_rating"], 3.2)
        self.assertEqual(research["public_review_count"], 6)


if __name__ == "__main__":
    unittest.main()
