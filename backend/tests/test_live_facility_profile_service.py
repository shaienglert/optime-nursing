import unittest

from app.services.live_facility_profile_service import get_live_facility_profile


class LiveFacilityProfileServiceTests(unittest.TestCase):
    def test_palace_profile_is_identity_safe_and_complete(self):
        payload = get_live_facility_profile("105719")

        self.assertEqual(payload["facility"]["canonical_facility_id"], "CMS-105719")
        self.assertEqual(payload["facility"]["address"], "11215 SW 84TH STREET")
        self.assertEqual(payload["facility"]["phone"], "3052712225")
        self.assertEqual(payload["facility"]["must_not_merge"]["npi"], "1053752402")
        self.assertEqual(payload["summary"]["fact_count"], 62)
        self.assertEqual(payload["summary"]["verified_fact_count"], 19)
        self.assertEqual(payload["summary"]["unknown_fact_count"], 38)
        self.assertEqual(payload["summary"]["actionable_fact_count"], 43)
        self.assertEqual(payload["summary"]["evidence_confidence"], "MIXED")
        self.assertTrue(all(row["source_url_or_local_file"] for row in payload["facts"]))
        self.assertFalse(payload["safety_controls"]["email_send_enabled"])
        self.assertFalse(payload["safety_controls"]["production_write_enabled"])

    def test_other_ccn_is_rejected(self):
        with self.assertRaises(KeyError):
            get_live_facility_profile("105374")


if __name__ == "__main__":
    unittest.main()