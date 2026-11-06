"""Presentation-only source adapter. The decision engine must not import this module.

Google data is fetched on demand and never written or cached. U.S. News entries
require identity-bound, permission-reviewed attribution in the curated registry.
Legacy generic reputation snapshots and synthetic fixtures are never relabelled.
"""
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.services.public_reputation_runtime import _norm, _norm_addr, _row_identity_names

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data/nevada/verified/external_rating_sources.json"
DISCLAIMER = "External ratings are provided for reference only. They do not affect Oomnik's match ranking or break ties."


def _unavailable(provider, status="UNAVAILABLE"):
    return {"provider": provider, "status": status, "rating": None, "review_count": None,
            "recognition": None, "assessment_year": None, "observed_at": None,
            "source_url": None, "ranking_eligible": False}


def _source_url(value, hosts):
    try:
        parsed = urlparse(str(value or ""))
        return (str(value) if parsed.scheme == "https" and parsed.hostname in hosts
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443) else None)
    except ValueError:
        return None


def _records():
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return payload.get("records", []) if payload.get("schema_version") == 1 else []
    except (OSError, ValueError, AttributeError):
        return []


def _identity_matches(row, record):
    if not isinstance(record, dict) or record.get("identity_verified") is not True:
        return False
    name = _norm(record.get("facility_name"))
    address = _norm_addr(row.get("address") or row.get("facility_address"))
    return bool(name and address and _norm(row.get("city")) and
                str(record.get("canonical_facility_id")) == str(row.get("canonical_facility_id")) and
                name in _row_identity_names(row) and address == _norm_addr(record.get("address")) and
                _norm(row.get("city")) == _norm(record.get("city")))


def _google(row, config):
    unavailable = _unavailable("GOOGLE")
    place_id = config.get("place_id") if isinstance(config, dict) else None
    key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not isinstance(place_id, str) or not place_id.strip() or not key:
        return unavailable
    # A registry value cannot change the upstream host or inject a new path.
    if len(place_id) > 256 or not all(c.isalnum() or c in "_-" for c in place_id):
        return unavailable
    try:
        response = requests.get(
            "https://places.googleapis.com/v1/places/" + place_id,
            headers={"X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": "displayName,formattedAddress,rating,userRatingCount,googleMapsUri,businessStatus"},
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return unavailable
        # Confirm the returned business, not merely the curated lookup identifier.
        address = _norm_addr(payload.get("formattedAddress"))
        if (_norm((payload.get("displayName") or {}).get("text")) not in _row_identity_names(row)
                or _norm_addr(row.get("address") or row.get("facility_address")) not in address
                or _norm(row.get("city")) not in address
                or payload.get("businessStatus") == "CLOSED_PERMANENTLY"):
            return unavailable
        rating, count = payload.get("rating"), payload.get("userRatingCount")
        url = _source_url(payload.get("googleMapsUri"), {"google.com", "www.google.com", "maps.google.com"})
        if (isinstance(rating, bool) or not isinstance(rating, (int, float)) or
                not math.isfinite(rating) or not 1 <= rating <= 5 or
                isinstance(count, bool) or not isinstance(count, int) or count <= 0 or not url):
            return unavailable
        return {**unavailable, "status": "AVAILABLE", "rating": rating, "review_count": count,
                "source_url": url, "observed_at": datetime.now(timezone.utc).isoformat()}
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        # Never expose upstream responses or credentials in public errors.
        return _unavailable("GOOGLE", "SOURCE_UNAVAILABLE")


def _us_news(config):
    unavailable = _unavailable("US_NEWS")
    if not isinstance(config, dict) or config.get("display_permission_verified") is not True:
        return unavailable
    url = _source_url(config.get("source_url"), {"health.usnews.com"})
    if not url or not urlparse(url).path.startswith(("/best-senior-living/", "/best-nursing-homes/")):
        return unavailable
    year, label = config.get("assessment_year"), config.get("recognition")
    if isinstance(year, bool) or not isinstance(year, int) or not 2000 <= year <= date.today().year:
        return unavailable
    if not isinstance(label, str) or not label.strip() or len(label) > 250:
        return unavailable
    try:
        observed = date.fromisoformat(str(config.get("observed_at")))
        if observed > date.today():
            return unavailable
    except ValueError:
        return unavailable
    return {**unavailable, "status": "AVAILABLE", "recognition": label.strip(),
            "assessment_year": year, "source_url": url, "observed_at": observed.isoformat()}


def external_ratings_for_facility(row):
    result = {"canonical_facility_id": row.get("canonical_facility_id"), "disclaimer": DISCLAIMER,
              "ranking_eligible": False, "google": _unavailable("GOOGLE"), "us_news": _unavailable("US_NEWS")}
    if row.get("synthetic_pilot") is True:
        return result
    records = _records()
    if not isinstance(records, list):
        return result
    matches = [record for record in records if _identity_matches(row, record)]
    # Ambiguous mappings must be corrected before displaying an attribution.
    if len(matches) != 1:
        return result
    record = matches[0]
    result["google"] = _google(row, record.get("google"))
    result["us_news"] = _us_news(record.get("us_news"))
    return result
