from app.services import decision_engine_core as core


def test_haversine_zero_distance():
    assert core._haversine_miles(36.1716, -115.1391, 36.1716, -115.1391) == 0


def test_henderson_to_las_vegas_is_outside_tight_radius():
    miles = core._haversine_miles(36.0395, -114.9817, 36.1716, -115.1391)
    assert miles > 10


def test_radius_uses_explicit_miles_and_location_city():
    radius = core._requested_radius(
        {"locationImportant": "Yes", "maximumDistanceMiles": "15"},
        {"location_city": "HENDERSON"},
    )
    assert radius["miles"] == 15
    assert radius["city"] == "HENDERSON"
    assert radius["status"] == "RESOLVED_CITY_CENTROID"


def test_no_location_constraint_means_no_radius_gate():
    assert core._requested_radius(
        {"locationImportant": "No", "maximumDistanceMiles": "15"},
        {"location_city": "HENDERSON"},
    ) is None


def test_unknown_origin_is_not_silently_replaced_by_another_market():
    radius = core._requested_radius(
        {"locationImportant": "Yes", "maximumDistanceMiles": "15"},
        {"location_city": "RENO"},
    )
    assert radius["status"] == "ORIGIN_UNRESOLVED"
    assert radius["origin"] is None


def test_precise_address_is_not_replaced_by_city_centroid():
    radius = core._requested_radius(
        {
            "locationImportant": "Yes",
            "maximumDistanceMiles": "15",
            "referenceAddress": "333 S Valley View Blvd, Las Vegas NV 89107",
        },
        {"location_city": "LAS VEGAS"},
    )
    assert radius["status"] == "PRECISE_REFERENCE_REQUIRES_GEOCODING"
    assert radius["origin"] is None


def test_zip_reference_is_not_replaced_by_city_centroid():
    radius = core._requested_radius(
        {"locationImportant": "Yes", "maximumDistanceMiles": "10", "referenceAddress": "89107"},
        {"location_city": "LAS VEGAS"},
    )
    assert radius["status"] == "PRECISE_REFERENCE_REQUIRES_GEOCODING"


def test_state_names_and_abbreviations_normalize_to_same_scope():
    assert core._canonical_state("Nevada") == "NEVADA"
    assert core._canonical_state("NV") == "NEVADA"
    assert core._canonical_state("Florida") == "FLORIDA"
    assert core._canonical_state("FL") == "FLORIDA"


def test_state_is_independent_from_city_radius():
    radius = core._requested_radius(
        {"searchState": "Nevada", "locationImportant": "Yes", "maximumDistanceMiles": "15"},
        {"location_city": "HENDERSON"},
    )
    assert core._canonical_state("NV") == core._canonical_state("Nevada")
    assert radius["city"] == "HENDERSON"


def test_available_states_are_derived_from_canonical_inventory(monkeypatch):
    monkeypatch.setattr(core, "get_canonical_facility_index", lambda: {
        "a": {"state": "NV"},
        "b": {"state": "NV"},
        "c": {"state": "FL"},
        "d": {"state": ""},
    })
    assert core.available_search_states() == ["FLORIDA", "NEVADA"]
