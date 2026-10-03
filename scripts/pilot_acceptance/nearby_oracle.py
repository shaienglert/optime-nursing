"""Independent geography proof from raw synthetic points, never engine verdicts."""
from math import radians, sin, cos, atan2, sqrt


def nearby_evidence_key(facility, preferences):
    importance = preferences.get("nearby_importance", "No preference")
    categories = preferences.get("nearby_categories") or []
    fixture = facility.get("pilot_nearby_place_evidence") or {}
    neutral = (0, 0, 999.0)
    if not categories or importance == "No preference":
        return neutral
    if not (fixture.get("source") == "SYNTHETIC_PILOT_NEARBY_FIXTURE"
            and fixture.get("verification_status") == "VERIFIED"
            and fixture.get("canonical_facility_id") == facility.get("canonical_id")
            and fixture.get("synthetic_pilot") is True
            and fixture.get("not_real_world_evidence") is True):
        return neutral
    def distance(place):
        p1, p2 = radians(facility["latitude"]), radians(place["latitude"])
        dl = radians(place["longitude"] - facility["longitude"])
        a = sin((p2-p1)/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
        return round(3958.7613 * 2 * atan2(sqrt(a), sqrt(1-a)), 2)
    distances = [min(distance(place) for place in (fixture.get("places") or {}).get(category, []) if place.get("synthetic_pilot") is True)
                 for category in categories if (fixture.get("places") or {}).get(category)]
    coverage = len(distances) / len(categories)
    average = sum(distances)/len(distances) if distances else None
    band = 3 if coverage == 1 and average is not None and average <= 3 else 2 if coverage >= .5 and average is not None and average <= 5 else 1 if coverage > 0 else 0
    strength = band if importance == "Important" else min(band, 2)
    return (0, -strength, round(average, 2) if average is not None else 999.0)
