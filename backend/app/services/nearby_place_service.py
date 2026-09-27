from __future__ import annotations

import math
import os
import time
from typing import Any

import requests

OVERPASS_URL = os.getenv("OOMNIK_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
DEFAULT_RADIUS_METERS = int(os.getenv("OOMNIK_POI_RADIUS_METERS", "8047"))
_CACHE: dict[tuple[float, float, tuple[str, ...], int], tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = int(os.getenv("OOMNIK_POI_CACHE_TTL_SECONDS", "86400"))

CATEGORY_TAGS = {
    "Shopping": [("shop", None)],
    "Restaurants & cafés": [("amenity", "restaurant"), ("amenity", "cafe")],
    "Movie theater": [("amenity", "cinema")],
    "Bowling": [("leisure", "bowling_alley"), ("sport", "bowling")],
    "Senior center / social club": [("amenity", "social_facility"), ("amenity", "community_centre")],
    "Parks & walking paths": [("leisure", "park"), ("highway", "path")],
    "Gym / pool": [("leisure", "fitness_centre"), ("leisure", "swimming_pool")],
    "Library": [("amenity", "library")],
    "Place of worship": [("amenity", "place_of_worship")],
    "Medical center / doctors": [("amenity", "hospital"), ("amenity", "clinic"), ("amenity", "doctors")],
    "Pharmacy": [("amenity", "pharmacy")],
    "Public transportation": [("public_transport", "station"), ("amenity", "bus_station")],
    "Entertainment / cultural venues": [("amenity", "theatre"), ("amenity", "arts_centre"), ("tourism", "museum")],
}


def _distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def nearby_places(latitude: float, longitude: float, categories: list[str], radius_meters: int = DEFAULT_RADIUS_METERS) -> dict[str, Any]:
    requested = [c for c in categories if c in CATEGORY_TAGS]
    cache_key = (round(float(latitude), 5), round(float(longitude), 5), tuple(sorted(requested)), int(radius_meters))
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return {**cached[1], "cache": "HIT"}
    if not requested:
        return {"status": "NO_SUPPORTED_CATEGORIES", "places": {}, "radius_meters": radius_meters}
    clauses = []
    for category in requested:
        for key, value in CATEGORY_TAGS[category]:
            tag = f'["{key}"]' if value is None else f'["{key}"="{value}"]'
            clauses.extend([f'node(around:{radius_meters},{latitude},{longitude}){tag};', f'way(around:{radius_meters},{latitude},{longitude}){tag};'])
    query = "[out:json][timeout:15];(" + "".join(clauses) + ");out center tags;"
    response = requests.post(OVERPASS_URL, data={"data": query}, timeout=20)
    response.raise_for_status()
    found: dict[str, list[dict[str, Any]]] = {c: [] for c in requested}
    for element in response.json().get("elements", []):
        tags = element.get("tags") or {}
        lat = element.get("lat") or (element.get("center") or {}).get("lat")
        lon = element.get("lon") or (element.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        for category in requested:
            if any((key in tags if value is None else tags.get(key) == value) for key, value in CATEGORY_TAGS[category]):
                found[category].append({"name": tags.get("name") or category, "distance_miles": round(_distance_miles(latitude, longitude, float(lat), float(lon)), 2), "source": "OpenStreetMap/Overpass"})
    for category in found:
        found[category] = sorted(found[category], key=lambda x: x["distance_miles"])[:5]
    result = {"status": "OK", "places": found, "radius_meters": radius_meters, "source": "OpenStreetMap/Overpass", "cache": "MISS"}
    _CACHE[cache_key] = (time.time(), result)
    return result


def attach_nearby_place_fit(rows: list[dict[str, Any]], questionnaire_state: dict[str, Any]) -> None:
    categories = [str(x) for x in (questionnaire_state.get("nearbyPlaces") or []) if str(x) in CATEGORY_TAGS]
    importance = str(questionnaire_state.get("nearbyPlacesImportance") or "No preference")
    if not categories or importance == "No preference":
        return
    for row in rows:
        try:
            lat, lon = float(row.get("latitude")), float(row.get("longitude"))
        except (TypeError, ValueError):
            row["nearby_place_fit"] = {"status": "UNKNOWN", "reason": "facility coordinates unavailable", "importance": importance}
            continue
        try:
            lookup = nearby_places(lat, lon, categories)
        except requests.RequestException:
            row["nearby_place_fit"] = {"status": "UNKNOWN", "reason": "place lookup unavailable", "importance": importance}
            continue
        nearest = {}
        distances = []
        for category in categories:
            places = (lookup.get("places") or {}).get(category) or []
            if places:
                nearest[category] = places[0]
                distances.append(float(places[0]["distance_miles"]))
        coverage = len(nearest) / max(1, len(categories))
        avg = sum(distances) / len(distances) if distances else None
        # Deterministic ordinal fit only; no invented precision. Important preferences
        # separate candidates more strongly than nice-to-have preferences.
        if coverage == 1 and avg is not None and avg <= 3:
            band = 3
        elif coverage >= 0.5 and avg is not None and avg <= 5:
            band = 2
        elif coverage > 0:
            band = 1
        else:
            band = 0
        row["nearby_place_fit"] = {"status": "KNOWN", "importance": importance, "fit_band": band, "matched_categories": len(nearest), "requested_categories": len(categories), "nearest": nearest, "average_distance_miles": round(avg, 2) if avg is not None else None, "source": lookup.get("source")}


def nearby_rank_key(row: dict[str, Any], importance: str) -> tuple[Any, ...]:
    fit = row.get("nearby_place_fit") if isinstance(row.get("nearby_place_fit"), dict) else {}
    if fit.get("status") != "KNOWN":
        return (1, 0, 999.0)
    band = int(fit.get("fit_band") or 0)
    # Nice-to-have remains a weaker tie-break: same evidence, later in ranking tuple.
    strength = band if importance == "Important" else min(band, 2)
    return (0, -strength, float(fit.get("average_distance_miles") or 999.0))
