from __future__ import annotations
import json
from pathlib import Path
import re
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.facility import Facility, FacilityUser, FacilityCapability, FacilityAuditLog
from app.models.facility_questionnaire import FACILITY_ALIGNMENT, facility_questionnaire_v1_flat
from app.services.facility_profile_portal import save_capabilities, facility_profile_snapshot
from app.services.facility_questionnaire_details import normalize_details

ROOT = Path(__file__).resolve().parents[2]

class AlignmentContractTests(unittest.TestCase):
    def test_every_actual_consumer_question_has_an_explicit_provider_disposition(self):
        source = (ROOT / "frontend/src/lib/intake-questions.ts").read_text()
        ids = set(re.findall(r'id: "([^"]+)"', source))
        self.assertEqual(ids, set(FACILITY_ALIGNMENT["consumer_mapping"]))
        keys = {q["key"] for q in facility_questionnaire_v1_flat()}
        for row in FACILITY_ALIGNMENT["consumer_mapping"].values():
            self.assertTrue(row["reason"])
            self.assertTrue(set(row["provider_keys"]) <= keys)
            if row["mode"] == "EXISTING_DATA":
                self.assertTrue(row["source"])

    def test_no_duplicate_capability_keys(self):
        keys = [q["key"] for q in facility_questionnaire_v1_flat()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_critical_new_needs_are_not_collapsed_into_generic_support(self):
        mapping = FACILITY_ALIGNMENT["consumer_mapping"]
        self.assertIn("care_mechanical_lift", mapping["transferAssistance"]["provider_keys"])
        self.assertIn("care_secure_memory_unit", mapping["secureMemory"]["provider_keys"])
        self.assertIn("communication_medical_languages", mapping["medicalLanguage"]["provider_keys"])
        self.assertIn("pricing_mandatory_monthly", mapping["budget"]["provider_keys"])

class ProviderDetailStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.facility = Facility(cms_id="TEST-ALIGN", name="Test community", address="1 Test",
            city="Las Vegas", state="NV", zip_code="89101", beds=50)
        self.db.add(self.facility); self.db.flush()
        self.owner = FacilityUser(facility_id=self.facility.id, email="owner@test.invalid",
            password_hash="unused", role="OWNER", is_active=True)
        self.activities = FacilityUser(facility_id=self.facility.id, email="activities@test.invalid",
            password_hash="unused", role="ACTIVITIES", is_active=True)
        self.db.add_all([self.owner, self.activities]); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def save(self, answers, details=None, user=None):
        return save_capabilities(self.db, self.facility.id, (user or self.owner).id,
            answers, details=details)

    def question(self, key):
        return next(q for s in facility_profile_snapshot(self.db, self.facility.id)["sections"]
            for q in s["questions"] if q["key"] == key)

    def test_numeric_quote_and_evidence_survive_reload_as_provider_claim(self):
        self.save({"pricing_base_monthly": "YES"}, {"pricing_base_monthly": {
            "value": "5000", "conditions": "Private studio; housing only", "scope": "UNIT",
            "evidence_url": "https://example.com/rates", "observed_on": "2026-01-01"}})
        self.db.expire_all()
        q = self.question("pricing_base_monthly")
        self.assertEqual(q["details"]["value"], 5000)
        self.assertEqual(q["details"]["scope"], "UNIT")
        self.assertEqual(q["claim_status"], "PROVIDER_SUPPLIED")
        self.assertIn("budget", q["consumer_question_ids"])

    def test_limited_requires_conditions_when_details_are_submitted(self):
        with self.assertRaises(ValueError):
            self.save({"care_two_person_transfers": "LIMITED"}, {"care_two_person_transfers": {}})
        self.assertEqual(self.db.query(FacilityCapability).count(), 0)

    def test_provider_service_scope_and_delivery_survive_reload(self):
        self.save({"care_oxygen": "LIMITED"}, {"care_oxygen": {
            "scope": "SERVICE", "delivery": "THIRD_PARTY", "conditions": "External provider, daytime only"}})
        q = self.question("care_oxygen")
        self.assertEqual(q["value"], "LIMITED")
        self.assertEqual(q["details"]["delivery"], "THIRD_PARTY")

    def test_invalid_detail_rejects_whole_batch_before_any_write(self):
        with self.assertRaises(ValueError):
            self.save({"lifestyle_music": "YES", "pricing_base_monthly": "YES"},
                {"pricing_base_monthly": {"value": "NaN"}})
        self.assertEqual(self.db.query(FacilityCapability).count(), 0)
        self.assertEqual(self.db.query(FacilityAuditLog).count(), 0)

    def test_detail_cannot_bypass_answer_or_role_checks(self):
        with self.assertRaises(ValueError):
            self.save({}, {"care_oxygen": {"conditions": "yes"}})
        with self.assertRaises(PermissionError):
            self.save({"care_oxygen": "YES"}, {"care_oxygen": {"conditions": "trained staff"}},
                user=self.activities)
        self.assertEqual(self.db.query(FacilityCapability).count(), 0)

    def test_detail_only_edit_is_audited_and_counted_once(self):
        key = "communication_care_languages"
        self.save({key: "YES"}, {key: {"value": "English"}})
        result = self.save({key: "YES"}, {key: {"value": "English, Hebrew; day shift"}})
        self.assertEqual(result["updated"], 1)
        audit = self.db.query(FacilityAuditLog).filter(
            FacilityAuditLog.field_name == f"capability_details:{key}").order_by(FacilityAuditLog.id.desc()).first()
        self.assertIn("English", audit.old_value)
        self.assertIn("Hebrew", audit.new_value)
        again = self.save({key: "YES"}, {key: {"value": "English, Hebrew; day shift"}})
        self.assertEqual(again["unchanged"], 1)

    def test_unknown_clears_numeric_value_without_becoming_no(self):
        key = "pricing_base_monthly"
        self.save({key: "YES"}, {key: {"value": 5000}})
        self.save({key: "UNKNOWN"})
        q = self.question(key)
        self.assertEqual(q["value"], "UNKNOWN")
        self.assertNotIn("value", q["details"])

    def test_known_numeric_answer_cannot_omit_value(self):
        with self.assertRaises(ValueError):
            self.save({"social_resident_count": "YES"})

    def test_old_state_answers_remain_compatible(self):
        self.save({"dining_kosher": "LIMITED"})
        self.assertEqual(self.question("dining_kosher")["value"], "LIMITED")

    def test_bad_values_and_unknown_fields_are_rejected(self):
        number = {"response_kind": "number"}
        for value in ["Infinity", "-1", True, "not money"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_details(number, "YES", {"value": value})
        for data in [{"unknown_field": "x"}, {"evidence_url": "javascript:alert(1)"},
                     {"scope": "WHOLE_STATE"}, {"observed_on": "2999-01-01"}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                normalize_details({"response_kind": "state"}, "YES", data)

if __name__ == "__main__":
    unittest.main()

