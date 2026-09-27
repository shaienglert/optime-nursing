"""The search market comes from the place the family named, not from a person's name.

Henderson is one of the commonest surnames in the United States and also a city fifteen
miles from Las Vegas. A plain substring scan read "Dr. Henderson is her physician, she
lives in Miami" as a search in Henderson, Nevada -- the surname beat the city the family
actually stated, and the whole market was wrong. The same scan tested "miami" before
"north miami" and stopped at the first hit, so a family in North Miami was searched in
Miami.
"""
import unittest

from app.services.decision_engine_core import build_patient_needs_profile

BASE = {
    "relationship": "Mom", "ageGroup": "80-84", "assistanceLevel": "Fully independent",
    "memoryStatus": "No", "budget": 5000,
}


def city(text: str):
    return build_patient_needs_profile(BASE, text).get("location_city")


class PeopleAreNotPlacesTests(unittest.TestCase):
    def test_a_titled_name_does_not_set_the_market(self):
        self.assertEqual("MIAMI", city("Dr. Henderson is her physician. She lives in Miami and wants to stay there."))
        self.assertEqual("HIALEAH", city("Nurse Henderson visits weekly. She lives in Hialeah."))

    def test_a_titled_name_alone_invents_no_market(self):
        self.assertIsNone(city("Her doctor is Mr. Henderson. We have not decided on a city yet."))

    def test_someone_who_lives_in_henderson_still_gets_henderson(self):
        for text in (
            "My mother lives in Henderson and wants to stay close to her friends.",
            "She is in Henderson, Nevada.",
            "We are looking near Henderson.",
        ):
            with self.subTest(text=text):
                self.assertEqual("HENDERSON", city(text))


class LongerNameWinsTests(unittest.TestCase):
    def test_north_miami_is_not_miami(self):
        self.assertEqual("NORTH MIAMI", city("My mother is 84 and lives in North Miami."))

    def test_north_las_vegas_is_not_las_vegas(self):
        self.assertEqual("NORTH LAS VEGAS", city("My mother is 84 and lives in North Las Vegas."))

    def test_the_plain_cities_still_resolve(self):
        self.assertEqual("LAS VEGAS", city("My mother is 84 and lives in Las Vegas."))
        self.assertEqual("MIAMI", city("My mother is 84 and lives in Miami."))
        self.assertEqual("CORAL GABLES", city("My mother is 84 and lives in Coral Gables."))

    def test_the_place_the_family_named_wins_over_a_passing_mention(self):
        # "near Henderson" is where they want to look; Las Vegas is only context.
        self.assertEqual("HENDERSON", city("She has family all over Las Vegas, but we want somewhere near Henderson."))


if __name__ == "__main__":
    unittest.main()
