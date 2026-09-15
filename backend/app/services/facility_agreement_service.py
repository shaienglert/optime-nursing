from __future__ import annotations

"""Facility onboarding tracking -- registered, signed the Oomnik agreement, and
completed a verified profile. Set administratively (there is no self-serve
facility portal yet); read by placement_referral_service.py to decide Founding
Launch Offer eligibility.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.facility_agreement import FacilityAgreement


def get_agreement(db: Session, canonical_facility_id: str) -> Optional[FacilityAgreement]:
    return db.query(FacilityAgreement).filter(FacilityAgreement.canonical_facility_id == canonical_facility_id).first()


def mark_onboarding_complete(
    db: Session, canonical_facility_id: str, *, completed_at: Optional[datetime] = None
) -> FacilityAgreement:
    agreement = get_agreement(db, canonical_facility_id)
    if agreement is None:
        agreement = FacilityAgreement(canonical_facility_id=canonical_facility_id)
        db.add(agreement)
    agreement.onboarding_completed_at = completed_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(agreement)
    return agreement
