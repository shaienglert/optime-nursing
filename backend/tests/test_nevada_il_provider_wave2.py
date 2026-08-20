from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import get_canonical_facility_index, refresh_runtime_cache


EXPECTED = {
    "NV-PROVIDER-IL-DESTINATIONS-SPRING-VALLEY": {
        "city": "LAS VEGAS",
        "outside_care_allowed_verified": None,
        "home_health_referrals_verified": None,
    },
    "NV-PROVIDER-IL-DESTINATIONS-ALEXANDER": {
        "city": "NORTH LAS VEGAS",
        "outside_care_allowed_verified": "UNKNOWN",
        "home_health_referrals_verified": True,
    },
}


class NevadaILProviderWave2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("nevada_il_wave2_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("nevada_il_wave2_teardown")

    def test_wave2_provider_only_il_reaches_runtime(self) -> None:
        index = get_canonical_facility_index()
        self.assertTrue(set(EXPECTED).issubset(index), set(EXPECTED) - set(index))
        for canonical_id, expected in EXPECTED.items():
            row = index[canonical_id]
            self.assertEqual(row.get("canonical_type"), "INDEPENDENT_LIVING")
            self.assertEqual(row.get("license_status"), "UNREGULATED_SENIOR_HOUSING_PROVIDER_VERIFIED")
            self.assertEqual(row.get("source_truth_scope"), "PRIMARY_PROVIDER_IDENTITY_NO_CARE_LICENSE_INFERRED")
            self.assertEqual(row.get("city"), expected["city"])
            self.assertIn("INDEPENDENT_LIVING", row.get("housing_modalities") or [])
            self.assertIn("ACTIVE_ADULT_55_PLUS_APARTMENTS", row.get("housing_modalities") or [])

    def test_alexander_referral_does_not_become_care_delivery_or_outside_care_permission(self) -> None:
        row = get_canonical_facility_index()["NV-PROVIDER-IL-DESTINATIONS-ALEXANDER"]
        evidence = (row.get("provider_housing_evidence") or {}).get("evidence") or {}
        self.assertTrue(evidence.get("home_health_referrals_verified"))
        self.assertEqual(evidence.get("outside_care_allowed_verified"), "UNKNOWN")
        self.assertEqual(evidence.get("care_services_verified"), "UNKNOWN")
        self.assertNotIn("ASSISTED_LIVING", row.get("housing_modalities") or [])
        self.assertNotIn("MEMORY_CARE", row.get("housing_modalities") or [])


if __name__ == "__main__":
    unittest.main()
