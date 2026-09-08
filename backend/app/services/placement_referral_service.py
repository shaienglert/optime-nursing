from __future__ import annotations

"""OPTIME's placement-fee mechanism: a referral is created when a client asks OPTIME
to follow up with a facility, and OPTIME is paid only once retention is confirmed --
never on the referral itself. Business rules (specified 2026-09-08):

- Commission is due once the client has been in the facility 60 days without leaving
  by their own choice.
- Death between day 30 and day 60 (inclusive) still counts as a successful placement
  -- commission is due as soon as that's known, without waiting for day 60 to pass.
- A voluntary departure before day 60 waives the commission entirely.
- Nobody has a financial incentive to report an early voluntary departure the way the
  facility is incentivized (via its $250 credit) to report entry accurately -- so the
  explicit, deliberate rule is: if no departure is reported by day 60, OPTIME bills
  automatically. The burden is on reporting a departure to block billing, not on
  anyone confirming success.
- A death before day 30 is not covered by the user's 30-60 rule; treated here as
  waived, the same as an early voluntary departure, as the cautious default until
  told otherwise -- flagged explicitly rather than assumed silently.

billable_status() is a pure function of stored dates, not a scheduled job -- a missed
cron run must never silently cost OPTIME a payment or overcharge a facility.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.placement_referral import PlacementReferral

DEFAULT_COMMISSION_CENTS = 150000  # placeholder flat fee -- not yet given an exact figure; override per-referral until it is.
RETENTION_DAYS = 60
DEATH_STILL_PAYS_FROM_DAY = 30

VALID_DEPARTURE_REASONS = {"VOLUNTARY", "DECEASED"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    # SQLite (used locally/in tests) doesn't preserve tzinfo through DateTime(timezone=True)
    # columns the way Postgres (production) does -- a value read back can come back naive.
    # Treat a naive value as already-UTC rather than let comparisons raise.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def create_referral(
    db: Session,
    *,
    canonical_facility_id: str,
    case_token: Optional[str] = None,
    commission_amount_cents: int = DEFAULT_COMMISSION_CENTS,
) -> PlacementReferral:
    referral = PlacementReferral(
        canonical_facility_id=canonical_facility_id,
        case_token=case_token,
        commission_amount_cents=commission_amount_cents,
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)
    return referral


def get_referral_by_code(db: Session, referral_code: str) -> Optional[PlacementReferral]:
    return db.query(PlacementReferral).filter(PlacementReferral.referral_code == referral_code).first()


def confirm_entry(db: Session, referral_code: str, *, entry_date: datetime, confirmed_by: Optional[str] = None) -> PlacementReferral:
    referral = get_referral_by_code(db, referral_code)
    if referral is None:
        raise ValueError("unknown_referral_code")
    referral.entry_confirmed_at = entry_date
    referral.entry_confirmed_by = confirmed_by
    db.commit()
    db.refresh(referral)
    return referral


def report_departure(db: Session, referral_code: str, *, departure_date: datetime, reason: str) -> PlacementReferral:
    if reason not in VALID_DEPARTURE_REASONS:
        raise ValueError(f"invalid departure reason: {reason}")
    referral = get_referral_by_code(db, referral_code)
    if referral is None:
        raise ValueError("unknown_referral_code")
    referral.departure_date = departure_date
    referral.departure_reason = reason
    referral.departure_reported_at = _utc_now()
    db.commit()
    db.refresh(referral)
    return referral


def billable_status(referral: PlacementReferral, *, now: Optional[datetime] = None) -> str:
    """One of: PENDING_ENTRY, TRACKING, DUE, WAIVED_VOLUNTARY_DEPARTURE, WAIVED_EARLY_DECEASED."""
    if referral.entry_confirmed_at is None:
        return "PENDING_ENTRY"

    now = _aware(now or _utc_now())
    entry_confirmed_at = _aware(referral.entry_confirmed_at)
    day_30 = entry_confirmed_at + timedelta(days=DEATH_STILL_PAYS_FROM_DAY)
    day_60 = entry_confirmed_at + timedelta(days=RETENTION_DAYS)
    departure_date = _aware(referral.departure_date) if referral.departure_date is not None else None

    if referral.departure_reason == "VOLUNTARY" and departure_date is not None and departure_date < day_60:
        return "WAIVED_VOLUNTARY_DEPARTURE"

    if referral.departure_reason == "DECEASED" and departure_date is not None:
        if day_30 <= departure_date <= day_60:
            return "DUE"
        if departure_date < day_30:
            return "WAIVED_EARLY_DECEASED"
        # departure_date > day_60: retention already satisfied, falls through below.

    if now >= day_60:
        return "DUE"
    return "TRACKING"


def commission_due_cents(referral: PlacementReferral, *, now: Optional[datetime] = None) -> int:
    return referral.commission_amount_cents if billable_status(referral, now=now) == "DUE" else 0
