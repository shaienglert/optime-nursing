from __future__ import annotations

import math
import os
from typing import Any

import requests

OVERPASS_URL = os.getenv("OOMNIK_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
DEFAULT_RADIUS_METERS = int(os.getenv("OOMNIK_POI_RADIUS_METERS", "8047"))

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
    return {"status": "OK", "places": found, "radius_meters": radius_meters, "source": "OpenStreetMap/Overpass"}
