from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class FacilityAgreement(Base):
    """One row per facility: tracks when it completed onboarding (registered,
    signed the Oomnik agreement, and completed a verified profile).

    This single timestamp is the only thing placement_referral_service.py needs
    to decide Founding Launch Offer eligibility -- whether the facility's first
    placement is fee-free depends on completing onboarding within
    FOUNDING_OFFER_DAYS of OOMNIK_LAUNCH_AT. There is no self-serve facility
    portal yet, so onboarding_completed_at is set administratively (see
    facility_agreement_service.mark_onboarding_complete), not by facility action.
    """

    __tablename__ = "facility_agreements"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, unique=True, index=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
