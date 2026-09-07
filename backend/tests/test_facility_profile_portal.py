from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401 -- registers every model so Base.metadata.create_all resolves all FKs
from app.database import Base
from app.models.facility import (
    AnswerState,
    Facility,
    FacilityActivityCategory,
    FacilityAuditLog,
    FacilityCapability,
    FacilityPhoto,
    FacilityUser,
)
from app.services.facility_profile_portal import (
    PHOTO_TARGET,
    add_photo,
    deactivate_photo,
    facility_profile_snapshot,
    recompute_completeness,
    save_capabilities,
    search_claimable_facilities,
)


class FacilityProfilePortalTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

        self.facility = Facility(
            cms_id="295001",
            name="Las Ventanas at Summerlin",
            address="10401 W Charleston Blvd",
            city="Las Vegas",
            state="NV",
            zip_code="89135",
            beds=120,
            overall_rating=4,
        )
        self.other = Facility(
            cms_id="295002",
            name="Green Valley Ranch Senior Living",
            address="2000 Paseo Verde Pkwy",
            city="Henderson",
            state="NV",
            zip_code="89012",
            beds=88,
        )
        self.db.add_all([self.facility, self.other])
        self.db.commit()

        self.owner = FacilityUser(
            facility_id=self.facility.id,
            email="director@lasventanas.com",
            password_hash="x",
            role="OWNER",
            is_active=True,
            is_verified=True,
        )
        self.activities_lead = FacilityUser(
            facility_id=self.facility.id,
            email="activities@lasventanas.com",
            password_hash="x",
            role="ACTIVITIES",
            is_active=True,
            is_verified=True,
        )
        self.db.add_all([self.owner, self.activities_lead])
        self.db.commit()

    # ---------- claiming ----------

    def test_search_finds_by_partial_name_and_reports_claim_state(self) -> None:
        results = search_claimable_facilities(self.db, "ventanas")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["cms_id"], "295001")
        # A verified user already exists, so the operator is told before they try.
        self.assertTrue(results[0]["already_claimed"])

        unclaimed = search_claimable_facilities(self.db, "Green Valley")
        self.assertFalse(unclaimed[0]["already_claimed"])

    def test_search_ignores_one_character_queries(self) -> None:
        self.assertEqual(search_claimable_facilities(self.db, "L"), [])

    def test_search_can_narrow_by_state_and_city(self) -> None:
        self.assertEqual(len(search_claimable_facilities(self.db, "en", state="NV")), 2)
        self.assertEqual(len(search_claimable_facilities(self.db, "en", city="Henderson")), 1)
        self.assertEqual(search_claimable_facilities(self.db, "en", state="TX"), [])

    # ---------- the snapshot the editor renders ----------

    def test_snapshot_starts_every_question_unknown_and_carries_public_record(self) -> None:
        snapshot = facility_profile_snapshot(self.db, self.facility.id)

        self.assertEqual(snapshot["completeness"]["total_questions"], 33)
        self.assertEqual(snapshot["completeness"]["unanswered_count"], 33)
        self.assertEqual(snapshot["completeness"]["overall"], 0.0)

        values = {
            question["value"]
            for section in snapshot["sections"]
            for question in section["questions"]
        }
        self.assertEqual(values, {"UNKNOWN"})

        known = {row["key"]: row["value"] for row in snapshot["known_from_public_record"]}
        self.assertEqual(known["name"], "Las Ventanas at Summerlin")
        self.assertEqual(known["beds"], 120)
        self.assertTrue(
            all(row["source"] == "CMS" for row in snapshot["known_from_public_record"])
        )

    def test_snapshot_reports_seven_sections_covering_every_question(self) -> None:
        snapshot = facility_profile_snapshot(self.db, self.facility.id)
        self.assertEqual(len(snapshot["sections"]), 7)
        self.assertEqual(sum(s["total"] for s in snapshot["sections"]), 33)

    def test_missing_facility_is_a_value_error(self) -> None:
        with self.assertRaises(ValueError):
            facility_profile_snapshot(self.db, 9999)

    # ---------- answering ----------

    def test_saving_answers_records_provenance_and_an_audit_row(self) -> None:
        result = save_capabilities(
            self.db,
            self.facility.id,
            self.owner.id,
            {"medical_24_7_nursing": "YES", "dining_kosher": "LIMITED"},
        )
        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["unchanged"], 0)

        row = (
            self.db.query(FacilityCapability)
            .filter(FacilityCapability.capability == "medical_24_7_nursing")
            .one()
        )
        self.assertEqual(row.value, AnswerState.YES)
        self.assertEqual(row.source, "provider_portal")
        self.assertEqual(row.last_updated_by_user_id, self.owner.id)
        self.assertEqual(row.verification_count, 1)
        self.assertIsNotNone(row.verified_at)

        audits = self.db.query(FacilityAuditLog).all()
        self.assertEqual(len(audits), 2)
        self.assertEqual(
            {audit.field_name for audit in audits},
            {"capability:medical_24_7_nursing", "capability:dining_kosher"},
        )
        nursing_audit = next(a for a in audits if a.field_name.endswith("24_7_nursing"))
        self.assertIsNone(nursing_audit.old_value)
        self.assertEqual(nursing_audit.new_value, "YES")
        self.assertEqual(nursing_audit.user_role, "OWNER")

    def test_resaving_the_same_answer_is_not_a_change(self) -> None:
        save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "YES"})
        again = save_capabilities(
            self.db, self.facility.id, self.owner.id, {"dining_kosher": "YES"}
        )
        self.assertEqual(again["updated"], 0)
        self.assertEqual(again["unchanged"], 1)
        self.assertEqual(self.db.query(FacilityAuditLog).count(), 1)

    def test_changing_an_answer_keeps_the_previous_value_in_the_audit(self) -> None:
        save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "YES"})
        save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "NO"})
        latest = self.db.query(FacilityAuditLog).order_by(FacilityAuditLog.id.desc()).first()
        self.assertEqual(latest.old_value, "YES")
        self.assertEqual(latest.new_value, "NO")

    def test_answering_unknown_is_accepted_and_does_not_count_as_known(self) -> None:
        save_capabilities(
            self.db,
            self.facility.id,
            self.owner.id,
            {"lifestyle_pool": "YES", "lifestyle_music": "UNKNOWN"},
        )
        completeness = recompute_completeness(self.db, self.facility.id)
        # UNKNOWN is a legitimate answer to store -- the provider may genuinely not know --
        # but it must not be counted as coverage.
        self.assertEqual(completeness["unanswered_count"], 32)

    def test_unknown_capability_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_capabilities(self.db, self.facility.id, self.owner.id, {"lifestyle_helipad": "YES"})

    def test_unsupported_answer_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "MAYBE"})

    def test_a_user_from_another_facility_cannot_write(self) -> None:
        intruder = FacilityUser(
            facility_id=self.other.id,
            email="someone@greenvalley.com",
            password_hash="x",
            role="OWNER",
            is_active=True,
        )
        self.db.add(intruder)
        self.db.commit()
        with self.assertRaises(PermissionError):
            save_capabilities(self.db, self.facility.id, intruder.id, {"dining_kosher": "YES"})

    def test_a_deactivated_user_cannot_write(self) -> None:
        self.owner.is_active = False
        self.db.commit()
        with self.assertRaises(PermissionError):
            save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "YES"})

    def test_a_partially_permitted_submission_saves_nothing(self) -> None:
        # The activities lead may answer lifestyle questions but not clinical ones. A mixed
        # submission must fail whole: saving half of it would report a success the provider
        # cannot see through.
        with self.assertRaises(PermissionError):
            save_capabilities(
                self.db,
                self.facility.id,
                self.activities_lead.id,
                {"lifestyle_pool": "YES", "medical_24_7_nursing": "YES"},
            )
        self.assertEqual(self.db.query(FacilityCapability).count(), 0)
        self.assertEqual(self.db.query(FacilityAuditLog).count(), 0)

    def test_activities_role_can_answer_its_own_sections(self) -> None:
        result = save_capabilities(
            self.db,
            self.facility.id,
            self.activities_lead.id,
            {"lifestyle_gardening": "YES", "housing_pets_allowed": "YES", "dining_vegetarian": "YES"},
        )
        self.assertEqual(result["updated"], 3)

    def test_empty_submission_is_a_no_op(self) -> None:
        result = save_capabilities(self.db, self.facility.id, self.owner.id, {})
        self.assertEqual(result["updated"], 0)
        self.assertEqual(self.db.query(FacilityAuditLog).count(), 0)

    # ---------- photographs ----------

    def test_adding_and_removing_a_photo_is_audited_and_soft_deleted(self) -> None:
        added = add_photo(
            self.db,
            self.facility.id,
            self.owner.id,
            category="dining_room",
            url="https://cdn.example.com/dining.jpg",
            caption="Main dining room",
        )
        self.assertEqual(added["category"], "dining_room")

        photo = self.db.query(FacilityPhoto).one()
        self.assertEqual(photo.source, "provider_portal")
        self.assertEqual(photo.uploaded_by_user_id, self.owner.id)
        self.assertTrue(photo.is_active)

        deactivate_photo(self.db, self.facility.id, self.owner.id, photo.id)
        self.db.refresh(photo)
        self.assertFalse(photo.is_active)
        # The row survives so the audit trail still resolves to something.
        self.assertEqual(self.db.query(FacilityPhoto).count(), 1)
        self.assertEqual(
            {a.field_name for a in self.db.query(FacilityAuditLog).all()},
            {"photo:add", "photo:remove"},
        )

    def test_relative_photo_urls_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            add_photo(self.db, self.facility.id, self.owner.id, "general", "/uploads/1.jpg")

    def test_removing_a_photo_from_another_facility_fails(self) -> None:
        stray = FacilityPhoto(
            facility_id=self.other.id, category="general", url="https://cdn.example.com/x.jpg"
        )
        self.db.add(stray)
        self.db.commit()
        with self.assertRaises(ValueError):
            deactivate_photo(self.db, self.facility.id, self.owner.id, stray.id)

    def test_inactive_photos_leave_the_snapshot(self) -> None:
        added = add_photo(
            self.db, self.facility.id, self.owner.id, "general", "https://cdn.example.com/a.jpg"
        )
        deactivate_photo(self.db, self.facility.id, self.owner.id, added["photo_id"])
        self.assertEqual(facility_profile_snapshot(self.db, self.facility.id)["photos"], [])

    # ---------- completeness ----------

    def test_completeness_rises_with_answers_and_is_bucketed(self) -> None:
        dining_keys = ["dining_gluten_free", "dining_kosher", "dining_vegetarian", "dining_diabetic_meals"]
        save_capabilities(
            self.db, self.facility.id, self.owner.id, {key: "YES" for key in dining_keys}
        )
        completeness = recompute_completeness(self.db, self.facility.id)
        self.assertEqual(completeness["dining"], 1.0)
        self.assertEqual(completeness["medical"], 0.0)
        self.assertEqual(completeness["unanswered_count"], 29)
        # One of five buckets full.
        self.assertEqual(completeness["overall"], 0.2)

    def test_photo_completeness_saturates_at_the_target(self) -> None:
        for index in range(PHOTO_TARGET + 4):
            add_photo(
                self.db,
                self.facility.id,
                self.owner.id,
                "general",
                f"https://cdn.example.com/{index}.jpg",
            )
        completeness = recompute_completeness(self.db, self.facility.id)
        self.assertEqual(completeness["photos"], 1.0)
        self.assertEqual(completeness["photo_count"], PHOTO_TARGET + 4)

    def test_activity_completeness_counts_only_known_categories(self) -> None:
        self.db.add_all(
            [
                FacilityActivityCategory(
                    facility_id=self.facility.id, category="music", availability=AnswerState.YES
                ),
                FacilityActivityCategory(
                    facility_id=self.facility.id, category="gardening", availability=AnswerState.UNKNOWN
                ),
            ]
        )
        self.db.commit()
        completeness = recompute_completeness(self.db, self.facility.id)
        self.assertAlmostEqual(completeness["activity"], round(1 / 7, 4))

    def test_completeness_is_persisted_not_just_returned(self) -> None:
        save_capabilities(self.db, self.facility.id, self.owner.id, {"dining_kosher": "YES"})
        snapshot = facility_profile_snapshot(self.db, self.facility.id)
        stored = self.facility.profile_completeness
        self.assertIsNotNone(stored)
        self.assertEqual(stored.overall_score, snapshot["completeness"]["overall"])

    def test_snapshot_reports_whether_a_calendar_was_ever_imported(self) -> None:
        self.assertFalse(facility_profile_snapshot(self.db, self.facility.id)["activity_calendar_connected"])
        self.db.add(
            FacilityActivityCategory(
                facility_id=self.facility.id,
                category="music",
                availability=AnswerState.YES,
                import_source="google_calendar",
            )
        )
        self.db.commit()
        self.assertTrue(facility_profile_snapshot(self.db, self.facility.id)["activity_calendar_connected"])


if __name__ == "__main__":
    unittest.main()
