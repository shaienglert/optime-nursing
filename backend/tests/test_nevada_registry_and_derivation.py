from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401 -- registers every model so Base.metadata.create_all resolves all FKs
from app.database import Base
from app.ingestion.nevada_hcqc import (
    REGISTRY_PATH,
    federal_provider_number,
    endorsements_of,
    import_nevada_registry,
    read_rows,
    serves_seniors,
    synthetic_id,
)
from app.models.facility import (
    AnswerState,
    Facility,
    FacilityCapability,
    FacilityLicenseRecord,
    FacilityUser,
)
from app.services.capability_derivation import (
    CMS_CERTIFICATION,
    STATE_LICENSE,
    apply_derived_capabilities,
    backfill_derived_capabilities,
    derivable_answers,
)
from app.services.facility_profile_portal import facility_profile_snapshot, save_capabilities


def _row(**overrides) -> dict:
    base = {
        "source_county": "CLARK",
        "credential_type_code": "AGC",
        "name": "ATRIA SEVILLE",
        "credential_number": "1234-AGC-1",
        "status": "Active",
        "expiration_date": "12/31/2026",
        "disciplinary_action": "N",
        "address": "2000 W CHARLESTON BLVD",
        "city": "LAS VEGAS",
        "state": "NV",
        "zip": "89102",
        "phone": "702-555-0100",
        "bed_count": "144",
        "federal_provider_no": "",
        "derived_care_type": "ASSISTED_LIVING_COMMUNITY",
        "endorsement": "ASSISTED LIVING SERVICES, RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS",
        "serves_elderly": "Y",
        "beds_alzheimer": "0",
        "detail_url": "/Protected/INS/SODPublicView.aspx?LicenseeId=1",
    }
    base.update(overrides)
    return base


class NevadaRegistryIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def test_state_only_community_is_created_with_a_non_cms_identifier(self) -> None:
        result = import_nevada_registry(self.db, rows=[_row()])
        self.assertEqual(result["facilities_created"], 1)

        facility = self.db.query(Facility).one()
        self.assertEqual(facility.cms_id, "NV-1234-AGC-1")
        # Nothing may mistake a state licence for Medicare certification.
        self.assertFalse(facility.cms_id.isdigit())
        self.assertEqual(facility.name, "Atria Seville")
        self.assertEqual(facility.beds, 144)
        self.assertEqual(facility.state, "NV")

        record = self.db.query(FacilityLicenseRecord).one()
        self.assertEqual(record.state_license_number, "1234-AGC-1")
        self.assertEqual(record.state_care_type, "ASSISTED_LIVING_COMMUNITY")
        self.assertIn("ASSISTED LIVING SERVICES", record.state_endorsements)
        self.assertTrue(record.state_source_url.startswith("https://hcqc.nv.gov/"))

    def test_a_state_row_with_a_ccn_enriches_the_cms_facility_instead_of_duplicating_it(self) -> None:
        existing = Facility(
            cms_id="295001", name="Existing SNF", address="1 Main", city="Las Vegas",
            state="NV", zip_code="89135", beds=99,
        )
        self.db.add(existing)
        self.db.commit()

        result = import_nevada_registry(
            self.db,
            rows=[_row(federal_provider_no="295001", credential_number="99-SNF-1",
                       derived_care_type="SKILLED_NURSING", bed_count="120")],
        )
        self.assertEqual(result["cms_facilities_enriched"], 1)
        self.assertEqual(result["facilities_created"], 0)
        self.assertEqual(self.db.query(Facility).count(), 1)

        self.db.refresh(existing)
        # The federally audited bed count is not overwritten by a licence figure.
        self.assertEqual(existing.beds, 99)
        self.assertEqual(self.db.query(FacilityLicenseRecord).one().facility_id, existing.id)

    def test_reimporting_the_same_registry_creates_nothing_new(self) -> None:
        rows = [_row(), _row(name="LEGACY HOUSE", credential_number="2222-AGC-2")]
        import_nevada_registry(self.db, rows=rows)
        second = import_nevada_registry(self.db, rows=rows)
        self.assertEqual(second["facilities_created"], 0)
        self.assertEqual(self.db.query(Facility).count(), 2)
        self.assertEqual(self.db.query(FacilityLicenseRecord).count(), 2)

    def test_non_senior_and_inactive_rows_are_skipped(self) -> None:
        result = import_nevada_registry(
            self.db,
            rows=[
                _row(derived_care_type="NON_SENIOR_GROUP_HOME", serves_elderly="N",
                     endorsement="MENTAL ILLNESS", credential_number="3-AGC-3"),
                _row(derived_care_type="ADULT_DAY", serves_elderly="N", endorsement="N/A",
                     credential_number="4-ADC-4"),
                _row(status="Expired", credential_number="5-AGC-5"),
            ],
        )
        self.assertEqual(result["skipped_not_senior_housing"], 2)
        self.assertEqual(result["skipped_inactive"], 1)
        self.assertEqual(self.db.query(Facility).count(), 0)

    def test_skilled_nursing_is_senior_housing_even_though_the_flag_says_otherwise(self) -> None:
        # Every one of Clark County's forty SNFs reads serves_elderly=N with no senior
        # endorsement. An inclusion filter that trusted those fields dropped all of them.
        row = _row(derived_care_type="SKILLED_NURSING", serves_elderly="N",
                   endorsement="N/A", beds_alzheimer="0", federal_provider_no="295001")
        self.assertTrue(serves_seniors(row))

    def test_group_home_with_memory_care_is_included(self) -> None:
        self.assertTrue(serves_seniors(_row(derived_care_type="GROUP_HOME_WITH_MEMORY_CARE",
                                            serves_elderly="N", endorsement="N/A")))

    def test_behavioural_health_housing_needs_a_senior_endorsement_to_qualify(self) -> None:
        without = _row(derived_care_type="COMMUNITY_BASED_LIVING", serves_elderly="N",
                       endorsement="CBLA SERVICES PROVIDER", beds_alzheimer="0")
        self.assertFalse(serves_seniors(without))
        with_senior = _row(derived_care_type="COMMUNITY_BASED_LIVING", serves_elderly="N",
                           endorsement="CBLA RESIDENTIAL FACILITY, ALZHEIMER DISEASE")
        self.assertTrue(serves_seniors(with_senior))

    def test_referral_agencies_and_hospices_are_not_places_to_live(self) -> None:
        for care_type in ("REFERRAL_AGENCY", "HOSPICE", "ADULT_DAY"):
            self.assertFalse(serves_seniors(_row(derived_care_type=care_type, serves_elderly="Y")),
                             f"{care_type} must not be listed as senior housing")

    def test_the_real_registry_keeps_every_skilled_nursing_facility(self) -> None:
        # The count is data and moves with each refresh; the property is the contract.
        rows = read_rows()
        snf = [r for r in rows if r["derived_care_type"] == "SKILLED_NURSING"]
        self.assertGreater(len(snf), 30, "the registry should carry Clark County's nursing facilities")
        self.assertTrue(all(serves_seniors(r) for r in snf))

    def test_a_dedicated_alzheimer_home_counts_as_senior_housing_despite_the_flag(self) -> None:
        # The registry marks serves_elderly N on dedicated memory care homes; reading that
        # flag alone would drop 145 Clark County communities.
        row = _row(derived_care_type="MEMORY_CARE_DEDICATED_HOME", serves_elderly="N",
                   endorsement="ALZHEIMER DISEASE", beds_alzheimer="9")
        self.assertTrue(serves_seniors(row))

    def test_endorsement_parsing_drops_the_not_applicable_marker(self) -> None:
        self.assertEqual(endorsements_of({"endorsement": "N/A"}), [])
        self.assertEqual(
            endorsements_of({"endorsement": "ALZHEIMER DISEASE, MENTAL ILLNESS"}),
            ["ALZHEIMER DISEASE", "MENTAL ILLNESS"],
        )

    def test_a_sentinel_is_never_treated_as_a_certification_number(self) -> None:
        # ALiS writes "UNKNOWN" where it has no federal number. Read as an identity, it once
        # collapsed 291 separate communities onto a single facility row.
        for sentinel in ("UNKNOWN", "unknown", "N/A", "None", "-", ""):
            self.assertEqual(federal_provider_number({"federal_provider_no": sentinel}), "")
        self.assertEqual(federal_provider_number({"federal_provider_no": "295001"}), "295001")
        # Anything that is not six digits is not an identity, whatever the column is called.
        self.assertEqual(federal_provider_number({"federal_provider_no": "PENDING"}), "")

    def test_rows_sharing_a_sentinel_stay_separate_facilities(self) -> None:
        result = import_nevada_registry(self.db, rows=[
            _row(name="A AND J CARE HOME", credential_number="1-AGC-1", federal_provider_no="UNKNOWN"),
            _row(name="ABINGTON MANOR", credential_number="2-AGC-2", federal_provider_no="UNKNOWN"),
            _row(name="ACE CARE HOME", credential_number="3-AGC-3", federal_provider_no="UNKNOWN"),
        ])
        self.assertEqual(result["facilities_created"], 3)
        self.assertEqual(result["cms_facilities_enriched"], 0)
        self.assertEqual(self.db.query(Facility).count(), 3)
        ids = {f.cms_id for f in self.db.query(Facility).all()}
        self.assertEqual(ids, {"NV-1-AGC-1", "NV-2-AGC-2", "NV-3-AGC-3"})
        self.assertNotIn("UNKNOWN", ids)

    def test_synthetic_id_fits_the_column(self) -> None:
        self.assertLessEqual(len(synthetic_id("12345678901")), 20)


class CapabilityDerivationTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def _facility(self, cms_id: str) -> Facility:
        facility = Facility(cms_id=cms_id, name="Test", address="1 Main", city="Las Vegas",
                            state="NV", zip_code="89135")
        self.db.add(facility)
        self.db.commit()
        return facility

    def test_a_certified_nursing_facility_gets_the_four_certification_answers(self) -> None:
        facility = self._facility("295001")
        apply_derived_capabilities(self.db, facility.id)

        rows = {r.capability: r for r in self.db.query(FacilityCapability).all()}
        self.assertEqual(
            set(rows),
            {
                "continuum_skilled_nursing",
                "medical_24_7_nursing",
                "medical_physician_availability",
                "accessibility_wheelchair_access",
            },
        )
        for row in rows.values():
            self.assertEqual(row.value, AnswerState.YES)
            self.assertEqual(row.source, CMS_CERTIFICATION)
            self.assertTrue(row.notes, "a derived answer must say what it was read from")

    def test_rehabilitation_therapies_are_never_derived(self) -> None:
        # "Provide or obtain" is not the same as having a therapist on staff.
        facility = self._facility("295001")
        apply_derived_capabilities(self.db, facility.id)
        stored = {r.capability for r in self.db.query(FacilityCapability).all()}
        for key in ("rehab_physical_therapy", "rehab_occupational_therapy",
                    "rehab_speech_therapy", "continuum_rehabilitation"):
            self.assertNotIn(key, stored)

    def test_a_state_only_community_gets_nothing_from_certification(self) -> None:
        facility = self._facility("NV-1234-AGC-1")
        apply_derived_capabilities(self.db, facility.id)
        self.assertEqual(self.db.query(FacilityCapability).count(), 0)

    def test_an_alzheimer_endorsement_answers_both_memory_care_questions(self) -> None:
        facility = self._facility("NV-1234-AGC-1")
        self.db.add(FacilityLicenseRecord(facility_id=facility.id, state_license_number="1234-AGC-1",
                                          state_care_type="MEMORY_CARE_DEDICATED_HOME",
                                          state_endorsements="ALZHEIMER DISEASE"))
        self.db.commit()
        apply_derived_capabilities(self.db, facility.id)

        rows = {r.capability: r for r in self.db.query(FacilityCapability).all()}
        self.assertEqual(set(rows), {"medical_memory_care", "continuum_memory_care"})
        self.assertEqual(rows["medical_memory_care"].source, STATE_LICENSE)
        self.assertIn("Alzheimer", rows["medical_memory_care"].notes)

    def test_an_assisted_living_endorsement_answers_the_continuum_question(self) -> None:
        facility = self._facility("NV-2222-AGC-2")
        self.db.add(FacilityLicenseRecord(facility_id=facility.id, state_license_number="2222-AGC-2",
                                          state_care_type="ASSISTED_LIVING_COMMUNITY",
                                          state_endorsements="ASSISTED LIVING SERVICES"))
        self.db.commit()
        apply_derived_capabilities(self.db, facility.id)
        stored = {r.capability for r in self.db.query(FacilityCapability).all()}
        self.assertIn("continuum_assisted_living", stored)

    def test_a_provider_answer_is_never_overwritten_by_derivation(self) -> None:
        facility = self._facility("295001")
        user = FacilityUser(facility_id=facility.id, email="d@x.com", password_hash="x",
                            role="OWNER", is_active=True, is_verified=True)
        self.db.add(user)
        self.db.commit()

        # The operator says the memory care unit is closed. That is newer evidence than a licence.
        self.db.add(FacilityLicenseRecord(facility_id=facility.id, state_license_number="1",
                                          state_endorsements="ALZHEIMER DISEASE"))
        self.db.commit()
        save_capabilities(self.db, facility.id, user.id, {"medical_memory_care": "NO"})

        result = apply_derived_capabilities(self.db, facility.id)
        self.assertGreaterEqual(result["skipped_provider_answered"], 1)

        row = (
            self.db.query(FacilityCapability)
            .filter(FacilityCapability.capability == "medical_memory_care")
            .one()
        )
        self.assertEqual(row.value, AnswerState.NO)
        self.assertEqual(row.source, "provider_portal")

    def test_rerunning_derivation_changes_nothing(self) -> None:
        facility = self._facility("295001")
        first = apply_derived_capabilities(self.db, facility.id)
        second = apply_derived_capabilities(self.db, facility.id)
        self.assertEqual(first["written"], 4)
        self.assertEqual(second["written"], 0)
        self.assertEqual(second["unchanged"], 4)

    def test_derived_answers_reach_the_portal_snapshot_with_their_rationale(self) -> None:
        facility = self._facility("295001")
        apply_derived_capabilities(self.db, facility.id)
        snapshot = facility_profile_snapshot(self.db, facility.id)

        medical = next(s for s in snapshot["sections"] if s["section"] == "Medical")
        self.assertEqual(medical["prefilled_from_public_record"], 2)
        nursing = next(q for q in medical["questions"] if q["key"] == "medical_24_7_nursing")
        self.assertEqual(nursing["value"], "YES")
        self.assertEqual(nursing["source"], CMS_CERTIFICATION)
        self.assertIn("24 hours", nursing["note"])

        # Four fewer blanks for the provider to fill.
        self.assertEqual(snapshot["completeness"]["unanswered_count"], 29)

    def test_snapshot_labels_a_state_facility_by_its_licence_not_cms(self) -> None:
        facility = self._facility("NV-1234-AGC-1")
        self.db.add(FacilityLicenseRecord(facility_id=facility.id, state_license_number="1234-AGC-1",
                                          state_care_type="ASSISTED_LIVING_COMMUNITY"))
        self.db.commit()
        snapshot = facility_profile_snapshot(self.db, facility.id)
        sources = {row["source"] for row in snapshot["known_from_public_record"]}
        self.assertNotIn("CMS", sources)
        self.assertIn("NV state licence", sources)
        labels = {row["label"] for row in snapshot["known_from_public_record"]}
        self.assertIn("Licensed beds", labels)
        self.assertIn("State licence", labels)

    def test_backfill_walks_every_facility(self) -> None:
        self._facility("295001")
        self._facility("295002")
        self._facility("NV-3333-AGC-3")
        totals = backfill_derived_capabilities(self.db)
        self.assertEqual(totals["facilities"], 3)
        self.assertEqual(totals["written"], 8)  # four each for the two certified rows


class NevadaRegistryFileTests(unittest.TestCase):
    """The shipped extract is the input the ingestion is written against."""

    def test_the_registry_file_is_present_and_parses(self) -> None:
        self.assertTrue(REGISTRY_PATH.exists(), f"missing registry at {REGISTRY_PATH}")
        rows = read_rows()
        self.assertGreater(len(rows), 500)
        self.assertIn("credential_number", rows[0])
        self.assertIn("derived_care_type", rows[0])

    def test_the_extract_contains_the_communities_the_outreach_targets(self) -> None:
        names = {r["name"].upper() for r in read_rows()}
        for expected in ("ATRIA SEVILLE", "BROOKDALE LAS VEGAS", "MERRILL GARDENS AT GREEN VALLEY RANCH"):
            self.assertIn(expected, names)


if __name__ == "__main__":
    unittest.main()
