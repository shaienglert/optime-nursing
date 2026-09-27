"""The guard that stops ordinary supervision becoming a nursing requirement matched the
bare word "nursing", so merely mentioning a nursing home let the higher-acuity value
through. Found by running the ten acceptance cases against the pilot market.

The couple and stroke findings from the same run are covered on main by
test_pilot_couple_and_stroke_context.py.
"""
import unittest

from app.services.semantic_intent_ai import _ground_clinical_patch


class NursingSupervisionNeedsMoreThanTheWordTests(unittest.TestCase):
    def _patch_survives(self, user_text):
        result = {"questionnaire_patch": {"medicalCareProfile": {"needs": ["Nursing supervision"]}}}
        out = _ground_clinical_patch(result, user_text, {})
        return "Nursing supervision" in out["questionnaire_patch"]["medicalCareProfile"]["needs"]

    def test_passing_mention_of_a_nurse_is_not_a_care_need(self):
        for text in (
            "We toured a nursing home last week and did not like it.",
            "Her nurse suggested we start looking at communities.",
            "I work as a nurse so I know what to look for.",
        ):
            with self.subTest(text=text):
                self.assertFalse(self._patch_survives(text), f"{text!r} must not create a nursing requirement")

    def test_an_actual_nursing_need_still_gets_through(self):
        for text in (
            "She needs nursing supervision during the day.",
            "He requires skilled nursing care.",
            "She needs monitoring by a nurse overnight.",
            "We need a nurse on site around the clock.",
        ):
            with self.subTest(text=text):
                self.assertTrue(self._patch_survives(text), f"{text!r} states a nursing need and must be kept")

    def test_a_structured_client_selection_is_never_stripped(self):
        result = {"questionnaire_patch": {"medicalCareProfile": {"needs": ["Nursing supervision"]}}}
        out = _ground_clinical_patch(result, "no mention at all", {"medicalCareProfile": {"needs": ["Nursing supervision"]}})
        self.assertIn("Nursing supervision", out["questionnaire_patch"]["medicalCareProfile"]["needs"])


if __name__ == "__main__":
    unittest.main()
