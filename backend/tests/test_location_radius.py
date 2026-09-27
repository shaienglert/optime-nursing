"""Location completeness must reflect the structured intake answers."""

import pytest

from app.services.canonical_gap_policy import canonical_client_facts, gap_is_resolved
from app.services.decision_engine_core import _haversine_miles, _requested_radius


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ({"searchState": "Nevada", "locationImportant": "No"}, True),
        ({"searchState": "Nevada"}, False),
        ({"searchState": "Nevada", "locationImportant": "Yes"}, False),
        ({"searchState": "Nevada", "locationImportant": "Yes", "referenceAddress": "89107"}, True),
        ({"searchState": "Nevada", "locationImportant": "Yes", "referenceLocationValue": "Henderson"}, True),
        ({"locationImportant": "No"}, False),
    ],
)
def test_structured_location_completeness(answers, expected):
    facts = canonical_client_facts(answers, "")
    assert facts["market_location_known"] is expected
    assert gap_is_resolved("market_location", facts) is expected


def test_free_text_city_does_not_resolve_missing_structured_market():
    facts = canonical_client_facts({}, "Please search within 15 miles of Henderson.")
    assert facts["market_location_known"] is False


def test_henderson_radius_uses_henderson_origin():
    radius = _requested_radius(
        {"locationImportant": "Yes", "locationCity": "Henderson", "maximumDistanceMiles": "10"},
        {"location_city": "LAS VEGAS"},
    )
    assert radius["status"] == "RESOLVED_CITY_CENTROID"
    assert radius["city"] == "HENDERSON"
    assert _haversine_miles(*radius["origin"], 36.1716, -115.1391) > radius["miles"]


def test_precise_reference_requires_geocoding_before_radius_filter():
    radius = _requested_radius(
        {"locationImportant": "Yes", "referenceAddress": "89107", "maximumDistanceMiles": "15"},
        {"location_city": "LAS VEGAS"},
    )
    assert radius["status"] == "PRECISE_REFERENCE_REQUIRES_GEOCODING"
    assert radius["origin"] is None


def test_selected_intake_city_takes_precedence_over_city_in_free_text():
    radius = _requested_radius(
        {"locationImportant": "Yes", "referenceAddress": "Henderson", "maximumDistanceMiles": "10"},
        {"location_city": "LAS VEGAS"},
    )
    assert radius["city"] == "HENDERSON"
    assert radius["status"] == "RESOLVED_CITY_CENTROID"


def test_unresolved_selected_area_never_uses_unrelated_text_city():
    radius = _requested_radius(
        {"locationImportant": "Yes", "referenceAddress": "Reno", "maximumDistanceMiles": "10"},
        {"location_city": "LAS VEGAS"},
    )
    assert radius["city"] == "RENO"
    assert radius["status"] == "ORIGIN_UNRESOLVED"


@pytest.mark.parametrize("area", ["Spring Valley", "Paradise", "Enterprise", "Boulder City"])
def test_every_intake_area_has_a_radius_origin(area):
    radius = _requested_radius(
        {"locationImportant": "Yes", "referenceAddress": area, "maximumDistanceMiles": "10"},
        {},
    )
    assert radius["status"] == "RESOLVED_CITY_CENTROID"
