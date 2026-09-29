"""Honour a distance the family asked for, or say plainly that it was not applied.

The intake asks which address to measure from and how far still feels close enough. Until
now nothing measured anything: a family asking for ten miles was shown communities at
eleven, and the same five came back whether they said ten miles or a hundred. For a
daughter deciding whether she can visit after work that is often the whole question.

Two rules here, and the second matters as much as the first.

A stated radius is a hard limit. A community outside it is not presented as if it met the
requirement. When too few communities fit, the search is not quietly widened and the
family is not handed an empty page either: they are told how many fit, how many more fit a
little further out, and asked. Widening happens only after they say so.

And the radius is only applied when the reference point genuinely has coordinates. A
street address or a ZIP needs real geocoding, which this service does not do. Without
coordinates the radius is reported as not applied, with the reason, rather than quietly
ignored or pretended.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

EARTH_RADIUS_MILES = 3958.8

# What the intake offers. An expansion is proposed in five-mile steps beyond the request.
OFFERED_RADII = (10, 20, 30, 50, 100)
EXPANSION_STEP_MILES = 5
MAX_EXPANSION_MILES = 120


def haversine_miles(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
    latitude_1, longitude_1 = origin
    latitude_2, longitude_2 = destination
    d_lat = math.radians(latitude_2 - latitude_1)
    d_lon = math.radians(longitude_2 - longitude_1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(latitude_1)) * math.cos(math.radians(latitude_2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _coordinate(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def facility_point(record: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    latitude = _coordinate(record.get("latitude"))
    longitude = _coordinate(record.get("longitude"))
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def requested_radius_miles(questionnaire: Dict[str, Any]) -> Optional[float]:
    if str(questionnaire.get("locationImportant") or "").strip().lower() == "no":
        return None
    for key in ("maximumDistanceMiles", "customDistanceMiles"):
        raw = str(questionnaire.get(key) or "").strip()
        match = re.search(r"\d+(?:\.\d+)?", raw)
        if match:
            miles = float(match.group())
            if miles > 0:
                return miles
    return None


def approved_radius_miles(questionnaire: Dict[str, Any]) -> Optional[float]:
    """A wider radius the family explicitly agreed to after being asked."""
    raw = str(questionnaire.get("approvedSearchRadiusMiles") or "").strip()
    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        return None
    miles = float(match.group())
    return miles if miles > 0 else None


def city_centroid(city: str, canonical_rows: Iterable[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
    wanted = re.sub(r"[^a-z0-9 ]+", " ", str(city or "").lower()).strip()
    if not wanted:
        return None
    points = [
        point
        for record in canonical_rows
        if re.sub(r"[^a-z0-9 ]+", " ", str(record.get("city") or "").lower()).strip() == wanted
        for point in (facility_point(record),)
        if point
    ]
    if not points:
        return None
    return (
        sum(latitude for latitude, _ in points) / len(points),
        sum(longitude for _, longitude in points) / len(points),
    )


def resolve_reference_point(
    questionnaire: Dict[str, Any],
    canonical_rows: Iterable[Dict[str, Any]],
    *,
    location_city: Optional[str] = None,
) -> Dict[str, Any]:
    """Locate the point the family wants distances measured from.

    Coordinates supplied directly are exact. A named city can be placed at the middle of
    that city's communities, which is honest for "within ten miles of Las Vegas" and is
    reported as approximate. A street address, a neighbourhood or a ZIP cannot be placed
    without real geocoding, and is reported as unresolved rather than guessed at.
    """
    latitude = _coordinate(questionnaire.get("referenceLatitude"))
    longitude = _coordinate(questionnaire.get("referenceLongitude"))
    if latitude is not None and longitude is not None:
        return {
            "status": "RESOLVED",
            "method": "CLIENT_COORDINATES",
            "approximate": False,
            "label": str(questionnaire.get("referenceAddress") or questionnaire.get("referenceLocationValue") or "the address you gave"),
            "latitude": latitude,
            "longitude": longitude,
        }

    rows = list(canonical_rows)
    # The intake writes the chosen area into more than one field ("Las Vegas" into both
    # referenceAddress and referenceLocationValue). Each is tried on its own: joined, they
    # read "Las Vegas Las Vegas", which names no city, and the limit silently never applied
    # on the real site while every test that set one field passed.
    written_values: List[str] = []
    for key in ("referenceAddress", "referenceLocationValue", "locationCity", "city"):
        value = str(questionnaire.get(key) or "").strip()
        if value and value.lower() not in {v.lower() for v in written_values}:
            written_values.append(value)
    written = written_values[0] if written_values else ""

    for candidate in filter(None, (location_city, *written_values)):
        centroid = city_centroid(candidate, rows)
        if centroid:
            return {
                "status": "RESOLVED",
                "method": "CITY_CENTROID",
                "approximate": True,
                "label": str(candidate).upper(),
                "latitude": centroid[0],
                "longitude": centroid[1],
            }

    return {
        "status": "UNRESOLVED",
        "method": "NONE",
        "approximate": False,
        "label": written or None,
        "latitude": None,
        "longitude": None,
        "reason": (
            "A street address or ZIP has to be geocoded before distances can be measured, "
            "and no coordinates were available for it."
        ),
    }


def annotate_distances(rows: List[Dict[str, Any]], reference: Dict[str, Any], canonical_by_id: Dict[str, Dict[str, Any]]) -> None:
    """Put the distance from the reference point on every candidate, or None."""
    origin = (
        (reference.get("latitude"), reference.get("longitude"))
        if reference.get("status") == "RESOLVED"
        else None
    )
    for row in rows:
        point = facility_point(canonical_by_id.get(str(row.get("canonical_facility_id") or "")) or {})
        row["distance_miles"] = (
            round(haversine_miles(origin, point), 1) if origin and point else None
        )


def _next_radius_above(distance: float) -> float:
    step = EXPANSION_STEP_MILES
    return min(MAX_EXPANSION_MILES, math.ceil(distance / step) * step)


def plan_radius_scope(
    ranked_rows: List[Dict[str, Any]],
    questionnaire: Dict[str, Any],
    reference: Dict[str, Any],
) -> Dict[str, Any]:
    """Decide which communities the stated radius admits, and what to offer if too few.

    Returns the rows to present plus a scope block describing exactly what was applied,
    so the page can say what happened instead of implying a radius was honoured.
    """
    requested = requested_radius_miles(questionnaire)
    approved = approved_radius_miles(questionnaire)

    if requested is None:
        return {"rows": ranked_rows, "scope": {"requested_miles": None, "applied": False, "reason": "NO_RADIUS_REQUESTED"}}

    if reference.get("status") != "RESOLVED":
        # Never imply a limit was enforced when there was nothing to measure from.
        return {
            "rows": ranked_rows,
            "scope": {
                "requested_miles": requested,
                "applied": False,
                "reason": "REFERENCE_POINT_NOT_GEOCODED",
                "explanation": reference.get("reason"),
                "reference": {"label": reference.get("label"), "method": reference.get("method")},
                "client_action": "CONFIRM_LOCATION",
            },
        }

    effective = max(requested, approved) if approved else requested
    measurable = [row for row in ranked_rows if isinstance(row.get("distance_miles"), (int, float))]
    unmeasurable = [row for row in ranked_rows if not isinstance(row.get("distance_miles"), (int, float))]

    within = [row for row in measurable if row["distance_miles"] <= effective]
    beyond = sorted(
        (row for row in measurable if row["distance_miles"] > effective),
        key=lambda row: row["distance_miles"],
    )

    offer = None
    if beyond:
        proposed = _next_radius_above(beyond[0]["distance_miles"])
        additional = [row for row in beyond if row["distance_miles"] <= proposed]
        if additional:
            offer = {
                "miles": proposed,
                "additional_count": len(additional),
                "nearest_excluded_miles": beyond[0]["distance_miles"],
            }

    scope = {
        "requested_miles": requested,
        "effective_miles": effective,
        "applied": True,
        "expanded_by_client": bool(approved and approved > requested),
        "reference": {
            "label": reference.get("label"),
            "method": reference.get("method"),
            "approximate": bool(reference.get("approximate")),
        },
        "within_count": len(within),
        "excluded_count": len(beyond),
        "distance_unknown_count": len(unmeasurable),
        "expansion_offer": offer,
        # The search is never widened on the family's behalf.
        "client_action": "CONFIRM_EXPANSION" if offer else None,
    }
    # A community whose coordinates are missing is kept rather than silently dropped; the
    # count above says how many could not be measured.
    return {"rows": within + unmeasurable, "scope": scope}
