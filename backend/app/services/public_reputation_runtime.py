from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "public_reputation_snapshot.json"


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _norm_addr(value: Any) -> str:
    text = f" {_norm(value)} "
    for source, target in {
        " street ": " st ",
        " road ": " rd ",
        " avenue ": " ave ",
        " boulevard ": " blvd ",
        " drive ": " dr ",
        " north ": " n ",
        " south ": " s ",
        " east ": " e ",
        " west ": " w ",
    }.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _snapshot() -> Dict[str, Any]:
    if not SNAPSHOT_PATH.is_file():
        return {"records": [], "policy": {}}
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def get_public_reputation(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return governed reputation evidence only on deterministic identity match.

    Reputation is enrichment only. It cannot establish identity, care capability,
    licensing, or MUST eligibility. Missing evidence remains UNKNOWN.
    """
    name = _norm(row.get("facility_name") or row.get("name"))
    address = _norm_addr(row.get("address") or row.get("facility_address"))
    city = _norm(row.get("city"))
    if not name or not address:
        return {"rating": "UNKNOWN", "review_count": "UNKNOWN", "source": "UNKNOWN", "identity_verified": False}

    for record in _snapshot().get("records") or []:
        aliases = {_norm(record.get("facility_name"))}
        aliases.update(_norm(value) for value in record.get("aliases") or [])
        if name not in aliases:
            continue
        if address != _norm_addr(record.get("address")):
            continue
        record_city = _norm(record.get("city"))
        if city and record_city and city != record_city:
            continue
        rating = record.get("rating")
        review_count = record.get("review_count")
        return {
            "rating": float(rating) if isinstance(rating, (int, float)) else "UNKNOWN",
            "review_count": int(review_count) if isinstance(review_count, int) else "UNKNOWN",
            "source": (_snapshot().get("policy") or {}).get("source") or "PUBLIC_LOCAL_BUSINESS_INDEX",
            "source_entity_id": record.get("source_entity_id") or "UNKNOWN",
            "observed_at": _snapshot().get("observed_at") or "UNKNOWN",
            "identity_verified": True,
            "role": "REPUTATION_ENRICHMENT_ONLY",
        }

    return {"rating": "UNKNOWN", "review_count": "UNKNOWN", "source": "UNKNOWN", "identity_verified": False}


__all__ = ["get_public_reputation"]
