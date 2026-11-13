from __future__ import annotations

import unittest

from app.services.israel_facility_questionnaire import (
    QUESTIONS,
    SECTIONS,
    display_answers,
    public_schema,
    validate_questionnaire,
)
from app.services.israel_facility_registration import validate_registration
from tests.israel_registration_fixture import REQUIRED_QUESTIONNAIRE, registration


class QuestionnaireSchemaTests(unittest.TestCase):
    def test_keys_unique_and_every_choice_has_hebrew_label(self) -> None:
        keys = [q["key"] for s in SECTIONS for q in s["questions"]]
        self.assertEqual(len(keys), len(set(keys)))
        for question in QUESTIONS.values():
            for option in question.get("options", []):
                self.assertTrue(option["label"].strip())
        self.assertEqual(public_schema()["version"], "il-facility-questionnaire-v1")

    def test_core_questions_match_registration_fields(self) -> None:
        core = {k for k, q in QUESTIONS.items() if q["core"]}
        self.assertEqual(
            core,
            {
                "functional_levels_served",
                "moh_code_agreement",
                "license_authority",
                "license_id",
                "license_expiration_date",
                "monthly_price_ils",
                "deposit_ils",
            },
        )


class QuestionnaireValidationTests(unittest.TestCase):
    def test_required_answers_are_enforced(self) -> None:
        partial = dict(REQUIRED_QUESTIONNAIRE)
        partial.pop("staff_languages")
        with self.assertRaises(ValueError) as caught:
            validate_questionnaire(partial)
        self.assertIn("שפות", str(caught.exception))

    def test_empty_answers_stay_unknown_not_negative(self) -> None:
        answers = validate_questionnaire({**REQUIRED_QUESTIONNAIRE, "pets": "", "diets": [], "vacancy_by_level": {"NURSING": ""}})
        self.assertNotIn("pets", answers)
        self.assertNotIn("diets", answers)
        self.assertNotIn("vacancy_by_level", answers)

    def test_values_are_cleaned_and_checked(self) -> None:
        answers = validate_questionnaire(
            {
                **REQUIRED_QUESTIONNAIRE,
                "staff_languages": ["ru", "he", "ru"],
                "website": "example.co.il",
                "vacancy_by_level": {"NURSING": "waitlist"},
                "maintenance_fee_ils": "3500",
            }
        )
        self.assertEqual(answers["staff_languages"], ["HE", "RU"])
        self.assertEqual(answers["website"], "https://example.co.il")
        self.assertEqual(answers["vacancy_by_level"], {"NURSING": "WAITLIST"})
        self.assertEqual(answers["maintenance_fee_ils"], 3500)

        for bad in (
            {"staff_languages": ["KLINGON"]},
            {"contact_phone": "call me"},
            {"min_age": 300},
            {"no_such_question": "x"},
            {"monthly_price_ils": 5},  # core keys belong at the top level, not in questionnaire
        ):
            with self.assertRaises(ValueError):
                validate_questionnaire({**REQUIRED_QUESTIONNAIRE, **bad})

    def test_moh_agreement_and_funding_track_must_agree(self) -> None:
        with self.assertRaises(ValueError):
            validate_registration(registration(questionnaire={**REQUIRED_QUESTIONNAIRE, "payment_tracks": ["PRIVATE"]}))
        with self.assertRaises(ValueError):
            validate_registration(registration(moh_code_agreement="NO"))
        ok = validate_registration(
            registration(moh_code_agreement="NO", questionnaire={**REQUIRED_QUESTIONNAIRE, "payment_tracks": ["PRIVATE"]})
        )
        self.assertEqual(ok["questionnaire"]["payment_tracks"], ["PRIVATE"])

    def test_display_uses_hebrew_labels(self) -> None:
        sections = display_answers(
            validate_questionnaire({**REQUIRED_QUESTIONNAIRE, "shelter": "ROOM", "maintenance_fee_ils": 3500})
        )
        flat = {item["key"]: item["value"] for s in sections for item in s["items"]}
        self.assertEqual(flat["staff_languages"], "עברית, רוסית")
        self.assertEqual(flat["shelter"], 'ממ"ד בחדר')
        self.assertEqual(flat["maintenance_fee_ils"], "₪3,500")


if __name__ == "__main__":
    unittest.main()
