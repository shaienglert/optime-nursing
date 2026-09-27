"""Saying a need is not there must never create it.

"She does not need memory care" produced memory_care at HIGH. The denial was not
recognised -- each care area listed only a handful of set phrases and none of them covered
the ordinary way a family writes one -- so the words "memory care" went on to the keyword
table and created the requirement the sentence rules out. The same held for bathing,
dressing and medications.

This is the worst shape a mapping error can take: not a need invented out of unrelated
wording, but the exact opposite of what the family said.
"""
import unittest

from app.services.care_input_assertions import extract_care_denials
from app.services.decision_engine_core import build_patient_needs_profile

BASE = {
    "relationship": "Mom", "ageGroup": "80-84", "assistanceLevel": "",
    "memoryStatus": "", "budget": 6000, "distanceFromFamily": "Balanced location",
}

CARE_PARAMETERS = ("adl_support", "medication_support", "memory_care")


def care_needs(text: str):
    profile = build_patient_needs_profile(BASE, f"My mother is 84 in Las Vegas. {text}")
    return {
        str(need["parameter_id"]): f'{need.get("requirement_level")}={need.get("desired_value")}'
        for need in (profile.get("needs") or [])
        if isinstance(need, dict) and need.get("parameter_id") in CARE_PARAMETERS
        and str(need.get("desired_value")).upper() == "YES"
    }


class ADenialNeverCreatesTheNeedTests(unittest.TestCase):
    def test_the_plain_ways_a_family_writes_a_denial(self):
        for text in (
            "She does not need help with bathing.",
            "She doesn't need help with dressing.",
            "She does not need help with her medications.",
            "She does not need memory care.",
            "She doesn't need memory support.",
            "There is no need for help with bathing.",
            "She has never needed help with dressing.",
            "She does not use any medications.",
        ):
            with self.subTest(text=text):
                self.assertEqual({}, care_needs(text), f"{text!r} states the absence of a need")

    def test_the_detector_reports_the_denial_it_read(self):
        self.assertTrue(extract_care_denials("she does not need help with bathing")["adl"])
        self.assertTrue(extract_care_denials("she does not need help with her medications")["medication"])
        self.assertTrue(extract_care_denials("she does not need memory care")["memory"])


class RealNeedsAreUntouchedTests(unittest.TestCase):
    def test_a_stated_need_is_still_recorded(self):
        self.assertEqual("HIGH=YES", care_needs("She needs help with bathing and dressing.").get("adl_support"))
        self.assertEqual("HIGH=YES", care_needs("She needs help with her medications.").get("medication_support"))
        self.assertEqual("HIGH=YES", care_needs("She has dementia and needs memory care.").get("memory_care"))

    def test_the_detector_does_not_see_a_denial_in_a_request(self):
        for text in ("she needs help with bathing", "she needs help with her medications", "she has dementia and needs memory care"):
            with self.subTest(text=text):
                flags = extract_care_denials(text)
                self.assertFalse(flags["adl"] or flags["medication"] or flags["memory"])


if __name__ == "__main__":
    unittest.main()
