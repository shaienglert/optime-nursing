import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


def _new_referral_code() -> str:
    # Public, URL-safe, unguessable -- this is what a client redeems their benefit
    # with at the facility, and what the facility uses to confirm entry. Same
    # rationale as personal_report_case.case_token and facility_outreach's
    # response_token: not sequential/guessable.
    return uuid.uuid4().hex


class PlacementReferral(Base):
    """OPTIME's commission mechanism, end to end, for one client-facility referral.

    OPTIME is paid only on confirmed 60-day retention, never on the referral itself.
    The client's $500 benefit and the facility's $250 commission credit aren't just
    incentives -- redeeming the benefit is what makes the facility confirm the real
    entry date, which is the only signal this whole mechanism runs on. Everything
    about commission status (billable_status property below) is derived from that
    one date plus an optional departure report, never from a running scheduler --
    a missed cron job must never silently cost OPTIME a payment or overcharge a
    facility.
    """

    __tablename__ = "placement_referrals"

    id = Column(Integer, primary_key=True, index=True)
    referral_code = Column(String(32), nullable=False, unique=True, index=True, default=_new_referral_code)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    case_token = Column(String(32), nullable=True, index=True)

    benefit_amount_cents = Column(Integer, nullable=False, default=50000)
    facility_credit_amount_cents = Column(Integer, nullable=False, default=25000)
    commission_amount_cents = Column(Integer, nullable=False)

    entry_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    entry_confirmed_by = Column(String(255), nullable=True)

    departure_reported_at = Column(DateTime(timezone=True), nullable=True)
    departure_date = Column(DateTime(timezone=True), nullable=True)
    departure_reason = Column(String(32), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    notes = Column(Text, nullable=True)
