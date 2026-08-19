from __future__ import annotations

"""Verified adapter for Human Intelligence person-fit evidence.

The canonical integrity boundary is the decoded JSON payload, not the gzip/base64
transport wrapper. The wrapper can change without changing the evidence. This
adapter keeps the payload SHA-256 and record-count invariants hard, while reusing
the Human Intelligence signal semantics from ``human_intelligence_runtime``.
"""

import base64
import gzip
import hashlib
import json
from functools import lru_cache
from typing import Any, Dict, List

from app.services import human_intelligence_runtime as _base

build_human_intelligence_context = _base.build_human_intelligence_context
has_explicit_person_fit_preference = _base.has_explicit_person_fit_preference
person_fit_sort_key = _base.person_fit_sort_key


@lru_cache(maxsize=1)
def _verified_person_fit_index() -> Dict[str, Dict[str, Any]]:
    text = _base._PERSON_FIT_PATH.read_text(encoding="utf-8").strip()
    decoded = gzip.decompress(base64.b64decode(text, validate=True))
    actual_payload_sha = hashlib.sha256(decoded).hexdigest()
    if actual_payload_sha != _base._PERSON_FIT_PAYLOAD_SHA256:
        raise RuntimeError(
            "Las Vegas person-fit canonical payload checksum mismatch: "
            f"sha256={actual_payload_sha} expected={_base._PERSON_FIT_PAYLOAD_SHA256}"
        )

    payload = json.loads(decoded.decode("utf-8"))
    records = payload.get("records") or []
    if payload.get("record_count") != _base._PERSON_FIT_RECORD_COUNT or len(records) != _base._PERSON_FIT_RECORD_COUNT:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 367 source records")
    if payload.get("beds_known_count") != _base._PERSON_FIT_BEDS_KNOWN:
        raise RuntimeError("Las Vegas person-fit evidence must contain exactly 313 known official bed counts")

    return {
        str(row.get("canonical_id") or ""): row
        for row in records
        if row.get("canonical_id")
    }


def attach_human_person_fit(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> None:
    index = _verified_person_fit_index()
    preference = str(
        (((human_context.get("signals") or {}).get("community_size_preference") or {}).get("value") or "UNKNOWN")
    ).upper()

    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "")
        evidence = index.get(canonical_id) or {}
        beds = evidence.get("total_bed_count")
        if not isinstance(beds, int):
            beds = None
        band = _base._community_size_band(beds)
        fit = _base._size_fit(preference, band)
        row["human_person_fit"] = {
            "community_size": {
                "official_bed_count": beds if beds is not None else "UNKNOWN",
                "community_size_band": band,
                "preference": preference,
                "fit_score": fit if fit is not None else "UNKNOWN",
                "source": "Nevada HCQC / ALiS official detail" if beds is not None else "UNKNOWN",
                "evidence_class": "REGULATORY_VERIFIED" if beds is not None else "UNKNOWN",
            },
            "social_transition_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility social-engagement evidence is attached to this candidate yet.",
            },
            "independence_fit": {
                "status": "UNKNOWN",
                "reason": "No verified Nevada facility independence/lifestyle evidence is attached to this candidate yet.",
            },
        }


__all__ = [
    "attach_human_person_fit",
    "build_human_intelligence_context",
    "has_explicit_person_fit_preference",
    "person_fit_sort_key",
]
