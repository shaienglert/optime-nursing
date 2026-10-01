from __future__ import annotations

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

    def test_verified_active_current_license_passes(self) -> None:
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(license_status="Active", expiration_date="12/31/2099"), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_pass"])

    def test_missing_or_unverified_license_is_pending_never_pass(self) -> None:
        # Owner rule 2026-10-01: where a license is legally required, missing/unverified
        # is PENDING until verified -- not PASS, and not FAIL.
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        for extra in ({}, {"license_expired": False}, {"license_status": "Active"}, {"expiration_date": "12/31/2099"}, {"license_status": "UNKNOWN", "expiration_date": "12/31/2099"}):
            result = evaluate_candidate_intent(self._row(**extra), intent)
            self.assertIn("LICENSE_CURRENTLY_VALID", result["must_unknown"], msg=str(extra))
            self.assertEqual("PENDING_VERIFICATION", result["hard_gate"], msg=str(extra))

    def test_explicitly_inactive_license_fails(self) -> None:
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(license_status="Revoked", expiration_date="12/31/2099"), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_fail"])

    def test_license_not_required_for_independent_housing(self) -> None:
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        result = evaluate_candidate_intent(self._row(canonical_type="INDEPENDENT_LIVING"), intent)
        self.assertIn("LICENSE_CURRENTLY_VALID", result["must_pass"])

    def test_listing_filter_and_must_gate_share_one_authority(self) -> None:
        from app.services.facility_parameter_service import _nevada_listing_eligible
        base = {"canonical_type": "ASSISTED_LIVING_RFG", "nevada_license_id": "X1", "detail_url": "https://nvdpbh.aithent.com/x"}
        intent = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}]}
        for extra in ({"license_status": "Active", "expiration_date": "12/31/2099"}, {"license_status": "Active", "expiration_date": "01/01/2020"}, {"license_status": "Active"}, {"license_status": "Revoked", "expiration_date": "12/31/2099"}):
            row = {**base, **extra}
            listed = _nevada_listing_eligible(row)
            passed = "LICENSE_CURRENTLY_VALID" in evaluate_candidate_intent(self._row(**extra), intent)["must_pass"]
            self.assertEqual(listed, passed, msg=str(extra))


class LicenseExpiredHelperTests(unittest.TestCase):
    @classmethod
    def setUpContext(cls):
        from app.services import decision_engine_core
        return decision_engine_core

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
