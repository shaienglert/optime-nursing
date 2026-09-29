from unittest.mock import patch

from app.services.nearby_place_service import attach_nearby_place_fit


def test_successful_nearby_lookup_attaches_verified_places():
    rows = [{"latitude": 36.17, "longitude": -115.14}]
    questionnaire = {"nearbyPlaces": ["Parks & walking paths"], "nearbyPlacesImportance": "Important"}
    lookup = {
        "source": "OpenStreetMap/Overpass",
        "places": {"Parks & walking paths": [{"name": "A park", "distance_miles": 1.2}]},
    }
    with patch("app.services.nearby_place_service.nearby_places", return_value=lookup):
        attach_nearby_place_fit(rows, questionnaire)

    fit = rows[0]["nearby_place_fit"]
    assert fit["status"] == "KNOWN"
    assert fit["fit_band"] == 3
    assert fit["nearest"]["Parks & walking paths"]["name"] == "A park"
