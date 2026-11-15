"""Locality coordinates and distances for the Israeli market.

Coordinates are locality centre points (app/data/israel_localities.json; see its
"source" and "attribution"). They are approximate: a facility is placed at its own
coordinates when known, otherwise at its locality's centre. Facility street
addresses are not geocoded yet.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DATA = Path(__file__).resolve().parents[1] / "data" / "israel_localities.json"

# Spellings that differ between lists and the official settlement names.
_ALIASES = {
    "פתח תקוה": "פתח תקווה",
    "תל אביב": "תל אביב - יפו",
    "תל אביב יפו": "תל אביב - יפו",
    "יפו": "תל אביב - יפו",
    "דלית אל-כרמל": "דאלית אל-כרמל",
    "דלית אל כרמל": "דאלית אל-כרמל",
    "נצרת עילית": "נוף הגליל",
    "מודיעין": "מודיעין-מכבים-רעות",
    "דבורייה": "דבוריה",
    "ביתן אהרון": "ביתן אהרן",
    "רמת אפעל": "רמת גן",  # a neighbourhood of Ramat Gan
}


def _norm(name: str) -> str:  # noqa: D401
    text = str(name or "").strip()
    text = re.sub(r"[\"'״׳`]", "", text)
    text = text.replace("קריית ", "קרית ")
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _key(name: str) -> str:
    # Hyphen/space-insensitive comparison key.
    return re.sub(r"[\s\-]", "", _norm(name))


_ALIAS_KEYS: Dict[str, str] = {}


@lru_cache(maxsize=1)
def _index() -> Dict[str, Tuple[float, float, str]]:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    index: Dict[str, Tuple[float, float, str]] = {}
    for item in payload["localities"]:
        point = (float(item["lat"]), float(item["lon"]), item["name"])
        index.setdefault(_key(item["name"]), point)
        index.setdefault(_key(item["name_en"]).upper(), point)
    return index


def locate(name: Optional[str]) -> Optional[Tuple[float, float]]:
    if not name:
        return None
    key = _key(name)
    alias = _ALIAS_KEYS.get(key)
    for candidate in (key, _key(alias) if alias else None):
        if not candidate:
            continue
        hit = _index().get(candidate) or _index().get(candidate.upper())
        if hit:
            return hit[0], hit[1]
    return None


def km_between(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def facility_point(row: Dict[str, Any]) -> Tuple[Optional[Tuple[float, float]], str]:
    """(point, basis): the facility's own coordinates, else its locality centre."""
    lat, lon = row.get("latitude"), row.get("longitude")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return (float(lat), float(lon)), "FACILITY_COORDINATES"
    point = locate(row.get("city"))
    return (point, "LOCALITY_CENTRE") if point else (None, "UNKNOWN")


_ALIAS_KEYS.update({_key(k): v for k, v in _ALIASES.items()})
