"""A deliberately isolated record for exercising the provider portal.

It is never presented as a real community or as evidence for a family decision.  The
record exists solely so the portal can be reviewed end-to-end before email delivery is
configured.  Keeping it idempotent makes it safe to call from a deployed environment.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityUser

DEMO_CMS_ID = "OOMNIK-OPTICARE-DEMO"
DEMO_EMAIL = "portal-demo@opticare.example"


def ensure_opticare_demo(db: Session) -> dict[str, object]:
    facility = db.query(Facility).filter(Facility.cms_id == DEMO_CMS_ID).one_or_none()
    if facility is None:
        facility = Facility(
            cms_id=DEMO_CMS_ID,
            name="OPTICARE — Portal demonstration",
            address="1000 Demo Way",
            city="Las Vegas",
            state="NV",
            zip_code="89199",
            phone="(702) 555-0147",
            beds=72,
            source_name="OOMNIK_PORTAL_DEMO_ONLY",
            source_date="DEMO_2026-09-09",
            confidence_level="DEMO_ONLY",
        )
        db.add(facility)
        db.flush()

    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.facility_id == facility.id, FacilityUser.email == DEMO_EMAIL)
        .one_or_none()
    )
    if user is None:
        user = FacilityUser(
            facility_id=facility.id,
            email=DEMO_EMAIL,
            full_name="Oomnik Portal Reviewer",
            password_hash="DEMO_ONLY_NO_PASSWORD",
            role="ADMIN",
            is_active=True,
            is_verified=True,
            verification_method="DEMO_ACCESS",
            verified_badge=False,
        )
        db.add(user)
        db.flush()

    db.commit()
    return {
        "facility_id": facility.id,
        "user_id": user.id,
        "name": facility.name,
        "is_demo": True,
    }
