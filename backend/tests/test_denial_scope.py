"""A denial silences a need only where the family did not also state it.

Denial phrases were matched against the whole story, so a sentence about equipment the
family does not own deleted a clinical requirement the previous sentence had stated:

    "She uses oxygen continuously for COPD. There is no oxygen concentrator at home,
     so the community must supply it."

lost the oxygen requirement entirely, because "no oxygen" appeared somewhere in the text.
Dropping a clinical need is not a cosmetic error: it recommends communities that cannot
meet it.
"""
import unittest

from app.services.decision_engine_core import build_patient_needs_profile

BASE = {
    "relationship": "Mom", "ageGroup": "85-89",
    "assistanceLevel": "Needs assistance with bathing and dressing",
    "memoryStatus": "No", "budget": 8000,
}


def needs(text: str):
    profile = build_patient_needs_profile(BASE, text)
    return {
        str(need["parameter_id"]): f'{need.get("requirement_level")}={need.get("desired_value")}'
        for need in (profile.get("needs") or []) if isinstance(need, dict)
    }


class StatedNeedSurvivesADenialElsewhereTests(unittest.TestCase):
    def test_missing_equipment_at_home_does_not_delete_the_oxygen_need(self):
        got = needs(
            "My mother uses oxygen continuously for COPD. There is no oxygen concentrator "
            "at home, so the community must supply it."
        )
        self.assertEqual("HIGH=YES", got.get("respiratory_trach_vent"))

    def test_no_wound_care_at_home_does_not_delete_the_wound_need(self):
        got = needs(
            "My mother has a pressure wound on her heel. There is no wound care at home, "
            "so the community must provide it."
        )
        self.assertEqual("HIGH=YES", got.get("wound_care"))

    def test_the_need_survives_whichever_order_the_sentences_come_in(self):
        got = needs(
            "There is no wound care at home. My mother has a pressure wound on her heel "
            "that needs daily dressing changes."
        )
        self.assertEqual("HIGH=YES", got.get("wound_care"))


class GenuineDenialsStillSilenceTests(unittest.TestCase):
    def test_a_denial_about_the_person_still_removes_the_need(self):
        for text, parameter_id in (
            ("My mother is 86 and does not need oxygen.", "respiratory_trach_vent"),
            ("My mother is 86. She is not on oxygen.", "respiratory_trach_vent"),
            ("My mother is 86 and has no wounds.", "wound_care"),
            ("My father is 78 and does not need dialysis.", "dialysis_arrangements"),
            ("My mother walks independently and needs no transfer assistance.", "transfer_assistance"),
        ):
            with self.subTest(text=text):
                self.assertNotIn(parameter_id, needs(text))

    def test_a_denial_in_the_same_sentence_as_the_word_still_wins(self):
        # "not on dialysis yet" is about today, and today is what the search is for.
        self.assertNotIn(
            "dialysis_arrangements",
            needs("My father is not on dialysis yet, but his doctor says he will need dialysis within months."),
        )


if __name__ == "__main__":
    unittest.main()
