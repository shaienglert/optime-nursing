from unittest.mock import patch

from app.services.nearby_place_service import attach_nearby_place_fit
from copy import deepcopy


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

def test_entire_pilot_has_identity_bound_geographic_evidence():
    from scripts.build_synthetic_pilot_facilities import pilot_nearby_place_evidence
    rows = [{"canonical_facility_id": f"PILOT-NV-{i:03d}", "latitude": 36.17, "longitude": -115.14,
             "synthetic_pilot": True, "pilot_nearby_place_evidence": pilot_nearby_place_evidence(i, 36.17, -115.14, "2026-10-03")}
            for i in range(1, 51)]
    with patch("app.services.nearby_place_service.nearby_places", side_effect=AssertionError("Fictional facilities must not query real maps")):
        attach_nearby_place_fit(rows, {"nearbyPlaces": ["Library"], "nearbyPlacesImportance": "Important"})
    assert all(r["nearby_place_fit"]["status"] == "KNOWN" for r in rows)
    corrupted = deepcopy(rows[0])
    corrupted["pilot_nearby_place_evidence"]["canonical_facility_id"] = "OTHER"
    attach_nearby_place_fit([corrupted], {"nearbyPlaces": ["Library"], "nearbyPlacesImportance": "Important"})
    assert corrupted["nearby_place_fit"]["status"] == "UNKNOWN"
