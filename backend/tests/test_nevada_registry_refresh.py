from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "refresh_nevada_registry", REPO_ROOT / "scripts" / "refresh_nevada_registry.py"
)
refresh = importlib.util.module_from_spec(_SPEC)
sys.modules["refresh_nevada_registry"] = refresh
_SPEC.loader.exec_module(refresh)


def _alis(**overrides) -> dict:
    base = {
        "license_number": "1234-AGC-1",
        "license_type": "AGC",
        "facility_name": "ATRIA SEVILLE",
        "status": "Active",
        "expiration_date": "12/31/2026",
        "address": "2000 N RAMPART BLVD",
        "city": "LAS VEGAS",
        "state": "NV",
        "zip": "89128",
        "phone": "702-555-0100",
        "capacity": "144",
        "federal_provider_number": "",
        "detail_url": "https://nvdpbh.aithent.com/x",
        "memory_care_classification": "",
    }
    base.update(overrides)
    return base


def _registry(**overrides) -> dict:
    base = {
        "credential_type_code": "AGC",
        "name": "Atria Seville",
        "credential_number": "1234-AGC-1",
        "status": "Active",
        "expiration_date": "12/31/2026",
        "address": "2000 N Rampart Blvd",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89128",
        "phone": "702-555-0100",
        "bed_count": "144",
        "federal_provider_no": "",
        "derived_care_type": "ASSISTED_LIVING_COMMUNITY",
        "endorsement": "ASSISTED LIVING SERVICES",
        "serves_elderly": "Y",
        "beds_alzheimer": "0",
        "detail_url": "https://nvdpbh.aithent.com/x",
    }
    base.update(overrides)
    return base


class CredibilityGateTests(unittest.TestCase):
    """The gate that stops a login page from erasing the registry."""

    def test_an_empty_pull_is_refused(self) -> None:
        ok, reason = refresh.credibility_check(0, 611)
        self.assertFalse(ok)
        self.assertIn("zero records", reason)

    def test_a_collapse_is_refused_rather_than_written(self) -> None:
        # The classic failure: the session expires, the grid renders empty, and a good
        # registry is overwritten with a handful of rows.
        ok, reason = refresh.credibility_check(12, 611)
        self.assertFalse(ok)
        self.assertIn("80%", reason)

    def test_a_pull_just_above_the_floor_is_accepted(self) -> None:
        ok, _ = refresh.credibility_check(int(611 * 0.81), 611)
        self.assertTrue(ok)

    def test_a_pull_just_below_the_floor_is_refused(self) -> None:
        ok, _ = refresh.credibility_check(int(611 * 0.79), 611)
        self.assertFalse(ok)

    def test_growth_is_always_credible(self) -> None:
        ok, _ = refresh.credibility_check(700, 611)
        self.assertTrue(ok)

    def test_a_first_run_has_nothing_to_compare_against(self) -> None:
        ok, reason = refresh.credibility_check(400, 0)
        self.assertTrue(ok)
        self.assertIn("no previous registry", reason)


class NormalisationTests(unittest.TestCase):
    def test_a_known_licence_keeps_the_facts_alis_does_not_return(self) -> None:
        # Endorsements and the Alzheimer bed split are not in the results grid. Blanking
        # them on refresh would delete the evidence every memory-care derivation reads.
        existing = [_registry(endorsement="ALZHEIMER DISEASE", beds_alzheimer="9",
                              serves_elderly="N", derived_care_type="MEMORY_CARE_DEDICATED_HOME")]
        out = refresh.normalize([_alis()], existing)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["endorsement"], "ALZHEIMER DISEASE")
        self.assertEqual(out[0]["beds_alzheimer"], "9")
        self.assertEqual(out[0]["serves_elderly"], "N")

    def test_a_known_licence_keeps_its_richer_care_type(self) -> None:
        existing = [_registry(derived_care_type="ASSISTED_LIVING_WITH_MEMORY_CARE")]
        out = refresh.normalize([_alis()], existing)
        self.assertEqual(out[0]["derived_care_type"], "ASSISTED_LIVING_WITH_MEMORY_CARE")

    def test_live_fields_are_taken_from_the_refresh(self) -> None:
        existing = [_registry(status="Active", expiration_date="12/31/2026", bed_count="144")]
        out = refresh.normalize(
            [_alis(status="Expired", expiration_date="01/01/2027", capacity="150")], existing
        )
        self.assertEqual(out[0]["status"], "Expired")
        self.assertEqual(out[0]["expiration_date"], "01/01/2027")
        self.assertEqual(out[0]["bed_count"], "150")

    def test_a_new_skilled_nursing_licence_is_classified(self) -> None:
        out = refresh.normalize([_alis(license_type="SNF", license_number="9-SNF-9")], [])
        self.assertEqual(out[0]["derived_care_type"], "SKILLED_NURSING")

    def test_a_new_licence_with_confirmed_memory_evidence_is_classified_by_size(self) -> None:
        small = refresh.normalize(
            [_alis(license_number="a", capacity="10", memory_care_classification="CONFIRMED_OFFICIAL_DETAIL")], []
        )
        large = refresh.normalize(
            [_alis(license_number="b", capacity="80", memory_care_classification="CONFIRMED_OFFICIAL_DETAIL")], []
        )
        self.assertEqual(small[0]["derived_care_type"], "MEMORY_CARE_DEDICATED_HOME")
        self.assertEqual(large[0]["derived_care_type"], "MEMORY_CARE_DEDICATED_LARGE")

    def test_rows_without_a_credential_are_dropped(self) -> None:
        self.assertEqual(refresh.normalize([_alis(license_number="")], []), [])

    def test_every_registry_field_is_present_on_output(self) -> None:
        out = refresh.normalize([_alis()], [])
        self.assertEqual(set(out[0]), set(refresh.REGISTRY_FIELDS))


class CarryForwardTests(unittest.TestCase):
    def test_licence_types_outside_the_search_survive_the_refresh(self) -> None:
        # ALiS is queried for AGC/SNF/SFD. A CBL or HIC row is absent because it was never
        # asked for, which is not evidence the licence ended.
        existing = [
            _registry(credential_number="1-CBL-1", credential_type_code="CBL"),
            _registry(credential_number="2-HIC-2", credential_type_code="HIC"),
            _registry(credential_number="3-AGC-3", credential_type_code="AGC"),
        ]
        refreshed = refresh.normalize([_alis(license_number="4-AGC-4")], existing)
        merged, carried = refresh.merge_with_untouched(refreshed, existing)

        credentials = {r["credential_number"] for r in merged}
        self.assertEqual(carried, 2)
        self.assertIn("1-CBL-1", credentials)
        self.assertIn("2-HIC-2", credentials)
        # The AGC row WAS covered by the search and did not come back: that is a real closure.
        self.assertNotIn("3-AGC-3", credentials)
        self.assertIn("4-AGC-4", credentials)

    def test_a_refreshed_row_is_not_duplicated_by_the_carry_forward(self) -> None:
        existing = [_registry(credential_number="1-AGC-1", credential_type_code="AGC")]
        refreshed = refresh.normalize([_alis(license_number="1-AGC-1")], existing)
        merged, carried = refresh.merge_with_untouched(refreshed, existing)
        self.assertEqual(carried, 0)
        self.assertEqual(len(merged), 1)

    def test_merged_output_is_ordered_deterministically(self) -> None:
        existing = [_registry(credential_number="9-CBL-9", credential_type_code="CBL", name="Zeta")]
        refreshed = refresh.normalize(
            [_alis(license_number="1-AGC-1", facility_name="ALPHA"),
             _alis(license_number="2-AGC-2", facility_name="MIDDLE")],
            existing,
        )
        merged, _ = refresh.merge_with_untouched(refreshed, existing)
        self.assertEqual([r["name"] for r in merged], ["ALPHA", "MIDDLE", "Zeta"])


class ScopeFilterTests(unittest.TestCase):
    """ALiS answers statewide; the registry declares one county."""

    def test_clark_zips_are_kept_and_others_dropped(self) -> None:
        self.assertTrue(refresh.in_clark_county({"zip": "89135", "city": "LAS VEGAS"}))
        self.assertTrue(refresh.in_clark_county({"zip": "89012", "city": "HENDERSON"}))
        self.assertFalse(refresh.in_clark_county({"zip": "89502", "city": "RENO"}))
        self.assertFalse(refresh.in_clark_county({"zip": "89701", "city": "CARSON CITY"}))

    def test_the_city_decides_only_when_the_zip_cannot(self) -> None:
        self.assertTrue(refresh.in_clark_county({"zip": "", "city": "Boulder City"}))
        self.assertTrue(refresh.in_clark_county({"zip": "n/a", "city": "laughlin"}))
        self.assertFalse(refresh.in_clark_county({"zip": "", "city": "Sparks"}))
        # A valid out-of-county ZIP is not overridden by a matching city string.
        self.assertFalse(refresh.in_clark_county({"zip": "89502", "city": "LAS VEGAS"}))

    def test_every_shipped_clark_record_passes_its_own_filter(self) -> None:
        records = json.loads(refresh.REGISTRY_PATH.read_text(encoding="utf-8"))["records"]
        missed = [r for r in records if not refresh.in_clark_county(r)]
        self.assertEqual(missed, [], f"{len(missed)} known-Clark rows would be filtered out")


class ShippedRegistryTests(unittest.TestCase):
    def test_the_committed_registry_matches_the_schema_the_refresh_writes(self) -> None:
        document = json.loads(refresh.REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(document["schema_version"], refresh.SCHEMA_VERSION)
        self.assertGreater(len(document["records"]), 500)
        self.assertEqual(set(document["records"][0]), set(refresh.REGISTRY_FIELDS))

    def test_a_refresh_of_the_real_registry_would_retain_almost_all_of_it(self) -> None:
        """Guards the carry-forward against a future narrowing of the search."""
        records = json.loads(refresh.REGISTRY_PATH.read_text(encoding="utf-8"))["records"]
        covered = {"AGC", "SNF", "SFD"}
        outside = [r for r in records if r["credential_type_code"].upper() not in covered]
        # Even if ALiS returned nothing at all, the carry-forward alone holds these; the
        # credibility gate then refuses the write, which is the intended outcome.
        merged, carried = refresh.merge_with_untouched([], records)
        self.assertEqual(carried, len(outside))
        ok, _ = refresh.credibility_check(len(merged), len(records))
        self.assertFalse(ok, "an empty ALiS pull must never pass the gate")


if __name__ == "__main__":
    unittest.main()
