from __future__ import annotations

import sys
import unittest

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent


class LicenseValidityGateTests(unittest.TestCase):
    def _row(self, **extra) -> dict:
        row = {
            "canonical_facility_id": "TEST-1",
            "facility_name": "Test Facility",
            "city": "LAS VEGAS",
            "state": "NV",
            "canonical_type": "ASSISTED_LIVING_RFG",
        }
        row.update(extra)
        return row

    def test_license_currently_valid_is_always_present_regardless_of_query_content(self) -> None:
        # Unlike every other MUST here, this one is never conditional on client wording.
        intent = build_client_intent({}, "just looking for somewhere nice", {"signals": {}, "household": {}}, {"signals": {}})
        keys = {item["key"] for item in intent["must_haves"]}
        self.assertIn("LICENSE_CURRENTLY_VALID", keys)

    def test_confirmed_expired_license_hard_fails(self) -> None:
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(license_expired=True), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_fail"])

    def test_confirmed_valid_license_passes(self) -> None:
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(license_expired=False), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_pass"])

    def test_missing_expiration_data_passes_rather_than_blocking(self) -> None:
        # No license_expired field at all (the shape of every pre-existing row/test
        # fixture in the whole suite) must never turn into UNKNOWN/PENDING noise.
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_pass"])
        self.assertNotIn("LICENSE_CURRENTLY_VALID", result["must_unknown"])
        self.assertNotIn("LICENSE_CURRENTLY_VALID", result["must_fail"])


class LicenseExpiredHelperTests(unittest.TestCase):
    @classmethod
    def setUpContext(cls):
        import app.main  # noqa: F401 -- registers app.services._patient_decision_engine_legacy
        return sys.modules["app.services._patient_decision_engine_legacy"]

    def setUp(self) -> None:
        self.legacy = self.setUpContext()

    def test_past_date_is_expired(self) -> None:
        self.assertTrue(self.legacy._license_expired("01/01/2020"))

    def test_future_date_is_not_expired(self) -> None:
        self.assertFalse(self.legacy._license_expired("12/31/2099"))

    def test_unknown_missing_and_garbage_values_are_unresolved_not_expired(self) -> None:
        for value in ("UNKNOWN", "", None, "not a date", "13/45/2026"):
            self.assertIsNone(self.legacy._license_expired(value), msg=f"value={value!r}")

    def test_iso_format_is_also_accepted(self) -> None:
        self.assertTrue(self.legacy._license_expired("2020-01-01"))
        self.assertFalse(self.legacy._license_expired("2099-12-31"))


if __name__ == "__main__":
    unittest.main()
