"""One authority for a facility's license standing.

Owner rule (2026-10-01): where a license is legally required, a missing or unverified
license is not a PASS; it is PENDING until verified, and never a final recommendation.
Independent / unregulated senior housing is not licensed care, so no care license is
required for it (its care limits are handled by the care-capability evidence, not here).

Both the market listing filter and the LICENSE_CURRENTLY_VALID MUST read this function,
so the two can never disagree.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

LICENSE_NOT_REQUIRED_TYPES = frozenset({"INDEPENDENT_LIVING"})
ACTIVE_STATUSES = frozenset({"ACTIVE", "SYNTHETIC_PILOT_ACTIVE"})
NOT_ACTIVE_STATUSES = frozenset({"REVOKED", "SUSPENDED", "CLOSED", "INACTIVE", "EXPIRED", "SURRENDERED", "DENIED"})

VERIFIED_CURRENT = "VERIFIED_CURRENT"
NOT_REQUIRED = "NOT_REQUIRED"
EXPIRED = "EXPIRED"
NOT_ACTIVE = "NOT_ACTIVE"
UNVERIFIED = "UNVERIFIED"


def parse_expiration(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if not text or text.upper() == "UNKNOWN":
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def license_standing(record: Dict[str, Any], *, today: Optional[date] = None) -> str:
    today = today or datetime.now(timezone.utc).date()
    if str(record.get("canonical_type") or "").strip().upper() in LICENSE_NOT_REQUIRED_TYPES:
        return NOT_REQUIRED
    status = str(record.get("license_status") or "").strip().upper()
    expires = parse_expiration(record.get("expiration_date", record.get("license_expiration_date")))
    if (expires is not None and expires < today) or record.get("license_expired") is True:
        return EXPIRED
    if status in NOT_ACTIVE_STATUSES:
        return NOT_ACTIVE
    if status in ACTIVE_STATUSES and expires is not None:
        return VERIFIED_CURRENT
    return UNVERIFIED


__all__ = ["license_standing", "parse_expiration", "VERIFIED_CURRENT", "NOT_REQUIRED", "EXPIRED", "NOT_ACTIVE", "UNVERIFIED"]
