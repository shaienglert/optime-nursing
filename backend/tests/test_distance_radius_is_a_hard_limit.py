"""A stated radius is a limit, and an unmeasurable one is never reported as checked.

The family is asked how far they are willing to travel, and the answer went nowhere. A geo
bonus nudged the score, nothing was excluded, and the ranking sort key had no distance term
at all -- so a family asking for ten miles around Summerlin was shown communities at 11.1
and 11.2 miles among their five recommendations, and asking for a hundred miles instead
returned the very same five. For the daughter deciding whether she can get there after
work, that is not a detail; it is the question.

The rule now: search inside the stated radius only. When too few fit, say how many fit,
say how many more fit a little further out, and wait to be told to widen. And when the
reference point could not be placed on a map, report the radius as not applied rather than
implying it was honoured.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.location_radius import haversine_miles, plan_radius_scope, resolve_reference_point
from app.services.patient_decision_engine import run_patient_decision_engine

CARE_NEEDS = "Help with bathing, Help with dressing, Help with medications"
# Single authority (owner, 2026-10-01): decision facts come only from the Canonical
# Structured Profile. The radius behaviour is fed through a finished structured interview
# (the mother/bathing/area facts the old story repeated are already structured answers);
# free text without the interpreter would stay UNPROCESSED and leave the interview not ready.
READY_INTERVIEW = {"mandatoryComplete": True, "conditionalFollowUpsComplete": True}


def _run(miles: str | None, *, city: str = "Las Vegas", approved: str | None = None, limit: int = 8) -> dict:
    questionnaire = {
        "relationship": "Mom",
        "assistanceLevel": CARE_NEEDS,
        "budget": 8000,
        "moveTiming": "Planning ahead",
        "locationImportant": "yes",
        "locationCity": city,
        "maximumDistanceMiles": miles or "",
        "approvedSearchRadiusMiles": approved or "",
        "questionnaireCompletion": dict(READY_INTERVIEW),
    }
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"},
        clear=False,
    ):
        refresh_runtime_cache(f"radius-{miles}-{city}-{approved}")
        return run_patient_decision_engine(questionnaire, "", limit=limit)


class TheRadiusChangesTheAnswerTests(unittest.TestCase):
    """The check that would have caught this: a different radius must mean a different set."""

    def test_the_radius_bounds_the_search_rather_than_nudging_a_score(self):
        near = _run("10")["location_scope"]
        far = _run("100")["location_scope"]
        self.assertLess(
            near["within_count"], far["within_count"],
            "ten miles and a hundred miles admitted the same number of communities, so nothing was bounded",
        )
        self.assertGreater(near["excluded_count"], 0)
        self.assertEqual(0, far["excluded_count"])

    def test_a_tight_radius_and_a_wide_one_do_not_return_the_same_communities(self):
        # Four miles is tight enough to cut into the top of the ranking; ten is not, because
        # the highest-scoring communities all sit within six miles of the city centre.
        tight = _run("4")["results"]
        wide = _run("100")["results"]
        self.assertNotEqual(
            {row["canonical_facility_id"] for row in tight},
            {row["canonical_facility_id"] for row in wide},
            "the stated radius made no difference to the recommendations",
        )
        # The two lists are not nested, because each is cut to the same display limit: a
        # four-mile search promotes communities that rank below the top eight overall. What
        # must hold is that everything it shows really is inside four miles.
        for row in tight:
            self.assertLessEqual(row["distance_miles"], 4.0)

    def test_no_recommendation_sits_outside_the_radius_the_family_stated(self):
        result = _run("10")
        scope = result["location_scope"]
        self.assertTrue(scope["applied"])
        for row in result["results"]:
            self.assertIsNotNone(row["distance_miles"], f'{row["facility_name"]} was returned without a measured distance')
            self.assertLessEqual(
                row["distance_miles"], scope["effective_miles"],
                f'{row["facility_name"]} is {row["distance_miles"]} miles away and was presented as meeting a '
                f'{scope["effective_miles"]}-mile requirement',
            )


class EveryCardCarriesItsDistanceTests(unittest.TestCase):
    def test_the_distance_is_on_the_card_not_only_in_the_filter(self):
        for row in _run("20")["results"]:
            self.assertIn("distance_miles", row)
            self.assertIsInstance(row["distance_miles"], (int, float))


class TooFewMatchesAsksRatherThanWideningTests(unittest.TestCase):
    def test_the_family_is_told_what_lies_just_outside_and_asked(self):
        scope = _run("10")["location_scope"]
        offer = scope["expansion_offer"]
        if offer is None:
            self.skipTest("every matching community already fits inside ten miles of this reference point")
        self.assertGreater(offer["miles"], scope["effective_miles"])
        self.assertGreaterEqual(offer["additional_count"], 1)
        self.assertEqual("CONFIRM_EXPANSION", scope["client_action"], "an offer must wait for the family's answer")

    def test_widening_happens_only_with_the_family_s_approval(self):
        narrow = _run("10")
        widened = _run("10", approved="30")
        self.assertEqual(10.0, widened["location_scope"]["requested_miles"])
        self.assertEqual(30.0, widened["location_scope"]["effective_miles"])
        self.assertTrue(widened["location_scope"]["expanded_by_client"])
        self.assertGreaterEqual(
            len(widened["results"]), len(narrow["results"]),
            "approving a wider search must not return fewer communities",
        )

    def test_an_unapproved_search_is_never_silently_widened(self):
        self.assertFalse(_run("10")["location_scope"]["expanded_by_client"])


class AnUnplaceableReferencePointIsNeverPretendedTests(unittest.TestCase):
    def test_a_street_address_reports_the_radius_as_not_applied(self):
        reference = resolve_reference_point(
            {"referenceAddress": "4821 Palm Hollow Court, Apt 12"}, [{"city": "LAS VEGAS", "latitude": 36.1, "longitude": -115.1}]
        )
        self.assertEqual("UNRESOLVED", reference["status"])

        plan = plan_radius_scope([{"canonical_facility_id": "X", "distance_miles": None}], {"maximumDistanceMiles": "10"}, reference)
        self.assertFalse(plan["scope"]["applied"], "a radius was reported as applied with nothing to measure from")
        self.assertEqual("REFERENCE_POINT_NOT_GEOCODED", plan["scope"]["reason"])
        self.assertEqual("CONFIRM_LOCATION", plan["scope"]["client_action"])

    def test_a_named_city_is_placed_and_marked_approximate(self):
        rows = [
            {"city": "HENDERSON", "latitude": 36.03, "longitude": -114.98},
            {"city": "HENDERSON", "latitude": 36.05, "longitude": -114.94},
        ]
        reference = resolve_reference_point({"locationCity": "Henderson"}, rows)
        self.assertEqual("RESOLVED", reference["status"])
        self.assertEqual("CITY_CENTROID", reference["method"])
        self.assertTrue(reference["approximate"], "a city centroid is not the family's doorstep and must say so")

    def test_no_radius_asked_for_means_nothing_is_filtered(self):
        rows = [{"canonical_facility_id": "A", "distance_miles": 90.0}]
        plan = plan_radius_scope(rows, {"locationImportant": "no", "maximumDistanceMiles": "10"}, {"status": "RESOLVED"})
        self.assertEqual(rows, plan["rows"])
        self.assertFalse(plan["scope"]["applied"])


class TheMeasurementItselfTests(unittest.TestCase):
    def test_distance_between_two_known_points(self):
        # Las Vegas to Henderson is about 13 miles; the tolerance keeps this a check on the
        # formula rather than on the third decimal.
        self.assertAlmostEqual(13.0, haversine_miles((36.1699, -115.1398), (36.0395, -114.9817)), delta=1.5)

    def test_a_community_with_no_coordinates_is_kept_and_counted_not_silently_dropped(self):
        rows = [
            {"canonical_facility_id": "NEAR", "distance_miles": 4.0},
            {"canonical_facility_id": "NO_COORDS", "distance_miles": None},
        ]
        plan = plan_radius_scope(rows, {"maximumDistanceMiles": "10"}, {"status": "RESOLVED"})
        self.assertIn("NO_COORDS", {row["canonical_facility_id"] for row in plan["rows"]})
        self.assertEqual(1, plan["scope"]["distance_unknown_count"])


if __name__ == "__main__":
    unittest.main()


class TheScopeReachesTheFamilyTests(unittest.TestCase):
    """The page can only say whether the limit was applied if the response carries it.

    PatientDecisionEngineOut drops any field it does not declare, so location_scope was
    computed and then thrown away on its way to the browser.
    """

    def test_the_http_response_model_keeps_the_location_scope(self):
        from app.main import PatientDecisionEngineOut

        scope = {"requested_miles": 10.0, "applied": False, "reason": "REFERENCE_POINT_NOT_GEOCODED"}
        body = PatientDecisionEngineOut(
            patient_needs_profile={}, results=[], result_count=0, total_candidates_scored=0,
            availability_policy="confirm directly", location_scope=scope,
        ).model_dump()
        self.assertEqual(scope, body["location_scope"])


class TheAreaAsTheIntakeWritesItTests(unittest.TestCase):
    """The tests above name the area in locationCity. The intake does not: it writes the chosen area into referenceAddress AND referenceLocationValue, and
    the story need not mention it. Joined, those read "Las Vegas Las Vegas" and the limit
    never applied in any of the ten real browser journeys.
    """

    INTAKE = {"referenceAddress": "Las Vegas", "referenceLocationValue": "Las Vegas", "locationImportant": "Yes"}

    def test_the_duplicated_area_is_still_placed(self):
        rows = [
            {"city": "LAS VEGAS", "latitude": 36.17, "longitude": -115.14},
            {"city": "LAS VEGAS", "latitude": 36.11, "longitude": -115.17},
        ]
        reference = resolve_reference_point(dict(self.INTAKE), rows)
        self.assertEqual("RESOLVED", reference["status"])
        self.assertEqual("LAS VEGAS", reference["label"].upper())

    def test_the_limit_applies_to_an_intake_shaped_request(self):
        questionnaire = dict(
            self.INTAKE, relationship="Mom", assistanceLevel=CARE_NEEDS, budget=8000, moveTiming="Planning ahead",
            maximumDistanceMiles="10", questionnaireCompletion=dict(READY_INTERVIEW),
        )
        with patch.dict(
            "os.environ",
            {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"},
            clear=False,
        ):
            refresh_runtime_cache("radius-intake-shaped")
            result = run_patient_decision_engine(questionnaire, "", limit=8)
        scope = result["location_scope"]
        self.assertTrue(scope["applied"], scope)
        for card in result["results"]:
            self.assertIsNotNone(card.get("distance_miles"))
            self.assertLessEqual(card["distance_miles"], scope["effective_miles"])
