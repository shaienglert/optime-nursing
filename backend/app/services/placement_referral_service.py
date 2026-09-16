from __future__ import annotations

"""OPTIME's (Oomnik's) placement-fee mechanism: a referral is created when a client
asks OPTIME to follow up with a facility, and OPTIME is paid only once a qualifying
outcome is confirmed -- never on the referral itself. Business rules (revised
2026-09-15, supersedes the 2026-09-08 flat-fee version):

- Full 60-day retention: OPTIME is owed the full fee, FULL_FEE_CENTS ($1,999).
- Death before day 60 completes: OPTIME is owed 50% of the full fee,
  DEATH_PARTIAL_FEE_CENTS ($999.50) -- billable as soon as death is reported, no
  day-30 threshold (unlike the superseded 2026-09-08 version).
- A voluntary departure before day 60 waives the fee entirely -- the risk is
  OPTIME's.
- If no departure is reported by day 60, OPTIME bills automatically. The burden
  is on reporting a departure to block billing, not on anyone confirming success
  -- nobody has a financial incentive to report an early voluntary departure the
  way the facility is incentivized (via its Welcome Package credit) to report
  entry accurately.
- Founding Launch Offer: a facility that completes onboarding (registered,
  signed, verified profile -- see facility_agreement_service.py) within
  FOUNDING_OFFER_DAYS of OOMNIK_LAUNCH_AT gets its first placement fee-free,
  regardless of outcome. A facility that onboards later pays the normal fee
  schedule starting from its first placement -- this is a time-boxed launch
  acquisition incentive, not a standing "first placement is always free" rule.
- From a facility's second placement onward, the $500 client Welcome Package is
  funded half by the facility and half by OPTIME (OOMNIK_WELCOME_CONTRIBUTION_
  CENTS = $250) -- the facility funds the Welcome Package alone on a first
  placement, founding-free or not. This $250 is OPTIME's cost regardless of
  whether the fee itself ends up due (see net_income_cents) -- what happens if a
  second-placement resident then departs voluntarily (does OPTIME recover its
  $250?) is an explicitly open contract question, not decided here.

billable_status()/commission_due_cents() are pure functions of stored referral
dates, sibling-referral state (for placement numbering), and the facility's
agreement record -- never a scheduled job, so a missed cron run can't silently
cost OPTIME a payment or overcharge a facility.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.placement_referral import PlacementReferral
from app.services.facility_agreement_service import get_agreement

FULL_FEE_CENTS = 199900  # $1,999 -- full 60-day retention
DEATH_PARTIAL_FEE_CENTS = 99950  # $999.50 -- 50% of FULL_FEE_CENTS, death before day 60
WELCOME_PACKAGE_CENTS = 50000  # $500 total client Welcome Package
OOMNIK_WELCOME_CONTRIBUTION_CENTS = 25000  # $250 -- OPTIME's half, from the facility's 2nd placement onward
RETENTION_DAYS = 60
FOUNDING_OFFER_DAYS = 90  # days from OOMNIK_LAUNCH_AT a facility must complete onboarding within

VALID_DEPARTURE_REASONS = {"VOLUNTARY", "DECEASED"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    # SQLite (used locally/in tests) doesn't preserve tzinfo through DateTime(timezone=True)
    # columns the way Postgres (production) does -- a value read back can come back naive.
    # Treat a naive value as already-UTC rather than let comparisons raise.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _oomnik_launch_at() -> Optional[datetime]:
    """None until OPTIME_LAUNCH_DATE is configured -- deliberately: guessing a
    launch date would either grant a founding discount nobody authorized, or
    silently deny one to a facility that actually qualifies. No configured
    launch date means no facility can be founding-eligible yet, not a crash."""
    raw = os.getenv("OPTIME_LAUNCH_DATE")
    if not raw:
        return None
    try:
        return _aware(datetime.fromisoformat(raw))
    except ValueError:
        return None


def create_referral(db: Session, *, canonical_facility_id: str, case_token: Optional[str] = None) -> PlacementReferral:
    referral = PlacementReferral(canonical_facility_id=canonical_facility_id, case_token=case_token)
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


def placement_number(db: Session, referral: PlacementReferral) -> Optional[int]:
    """1-indexed: how many-eth confirmed placement this is for referral's facility.
    None if this referral's own entry isn't confirmed yet -- placement number
    isn't meaningful before that."""
    if referral.entry_confirmed_at is None:
        return None
    entry = _aware(referral.entry_confirmed_at)
    siblings = (
        db.query(PlacementReferral)
        .filter(
            PlacementReferral.canonical_facility_id == referral.canonical_facility_id,
            PlacementReferral.entry_confirmed_at.isnot(None),
        )
        .all()
    )
    earlier = 0
    for sibling in siblings:
        if sibling.id == referral.id:
            continue
        sibling_entry = _aware(sibling.entry_confirmed_at)
        if sibling_entry < entry or (sibling_entry == entry and sibling.id < referral.id):
            earlier += 1
    return earlier + 1


def is_founding_facility(db: Session, canonical_facility_id: str) -> bool:
    launch_at = _oomnik_launch_at()
    if launch_at is None:
        return False
    agreement = get_agreement(db, canonical_facility_id)
    if agreement is None or agreement.onboarding_completed_at is None:
        return False
    completed_at = _aware(agreement.onboarding_completed_at)
    return completed_at <= launch_at + timedelta(days=FOUNDING_OFFER_DAYS)


def billable_status(db: Session, referral: PlacementReferral, *, now: Optional[datetime] = None) -> str:
    """One of: PENDING_ENTRY, WAIVED_FOUNDING_FIRST_PLACEMENT, TRACKING,
    WAIVED_VOLUNTARY_DEPARTURE, DUE. DUE covers both the full-retention and the
    death-before-60 outcomes -- commission_due_cents distinguishes the amount."""
    if referral.entry_confirmed_at is None:
        return "PENDING_ENTRY"

    if placement_number(db, referral) == 1 and is_founding_facility(db, referral.canonical_facility_id):
        return "WAIVED_FOUNDING_FIRST_PLACEMENT"

    now = _aware(now or _utc_now())
    entry_confirmed_at = _aware(referral.entry_confirmed_at)
    day_60 = entry_confirmed_at + timedelta(days=RETENTION_DAYS)
    departure_date = _aware(referral.departure_date) if referral.departure_date is not None else None

    if referral.departure_reason == "VOLUNTARY" and departure_date is not None and departure_date < day_60:
        return "WAIVED_VOLUNTARY_DEPARTURE"

    if referral.departure_reason == "DECEASED" and departure_date is not None and departure_date < day_60:
        return "DUE"

    if now >= day_60 or (departure_date is not None and departure_date >= day_60):
        return "DUE"

    return "TRACKING"


def commission_due_cents(db: Session, referral: PlacementReferral, *, now: Optional[datetime] = None) -> int:
    """The gross fee OPTIME bills the facility -- unaffected by placement number
    or OPTIME's own Welcome Package contribution (see net_income_cents for that)."""
    if billable_status(db, referral, now=now) != "DUE":
        return 0
    entry_confirmed_at = _aware(referral.entry_confirmed_at)
    day_60 = entry_confirmed_at + timedelta(days=RETENTION_DAYS)
    departure_date = _aware(referral.departure_date) if referral.departure_date is not None else None
    if referral.departure_reason == "DECEASED" and departure_date is not None and departure_date < day_60:
        return DEATH_PARTIAL_FEE_CENTS
    return FULL_FEE_CENTS


def oomnik_welcome_contribution_cents(db: Session, referral: PlacementReferral) -> int:
    """OPTIME's own $250 toward the client's $500 Welcome Package, owed from the
    facility's 2nd confirmed placement onward -- independent of whether the fee
    itself ends up due (see module docstring)."""
    number = placement_number(db, referral)
    return OOMNIK_WELCOME_CONTRIBUTION_CENTS if number is not None and number >= 2 else 0


def facility_welcome_contribution_cents(db: Session, referral: PlacementReferral) -> int:
    return WELCOME_PACKAGE_CENTS - oomnik_welcome_contribution_cents(db, referral)


def net_income_cents(db: Session, referral: PlacementReferral, *, now: Optional[datetime] = None) -> int:
    """OPTIME's fee revenue minus its own Welcome Package contribution. Can be
    negative (e.g. a 2nd+ placement that departs voluntarily: $0 fee, $250
    already spent on the Welcome Package)."""
    return commission_due_cents(db, referral, now=now) - oomnik_welcome_contribution_cents(db, referral)
