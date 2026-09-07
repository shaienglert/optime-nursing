"""Answer the questionnaire items that a licence or certification already settles.

A provider opening the portal to thirty-three blank rows is being asked to type facts a
regulator has already published. Some of those rows can be filled before they arrive, and
filling them is not a shortcut -- it is the difference between asking someone to complete a
form and showing them we did our homework first.

The bar for deriving an answer is deliberately high, and only two kinds of fact clear it.

  A licence endorsement is a *statement*. Nevada endorsing a community for ALZHEIMER
  DISEASE, or licensing dedicated Alzheimer beds, is the state asserting memory care exists
  there. Recording that is repeating a public fact, not guessing.

  A certification requirement is *definitional*. Medicare certification as a skilled nursing
  facility is not a rating; it is a status that cannot be held without meeting participation
  requirements, among them round-the-clock licensed nursing and physician availability. A
  certified facility that lacked those would lose the certification the answer is read from.

Everything else stays UNKNOWN. In particular the rehabilitation therapies are NOT derived:
a nursing facility must "provide or obtain" specialised rehabilitative services, and
"or obtain" is exactly the gap between a therapist on staff and a number to call. Inferring
in-house therapy from that wording is the kind of guess this product exists to refuse.

A provider's own answer always outranks a derived one. Derivation never overwrites a row
whose source is the portal, in either direction -- if an operator says their memory care
unit closed, that is newer and better evidence than the licence we read last month.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.facility import (
    AnswerState,
    Facility,
    FacilityCapability,
    FacilityLicenseRecord,
)

CMS_CERTIFICATION = "cms_certification"
STATE_LICENSE = "nv_state_license"
PORTAL_SOURCE = "provider_portal"

# Confidence is not a mood. A licence endorsement is a published regulatory statement about
# this specific community; a certification requirement is a condition of a status the
# facility currently holds. Both are strong, and both stop short of 1.0 because neither was
# observed by us and either can go stale between publications.
LICENSE_CONFIDENCE = 0.95
CERTIFICATION_CONFIDENCE = 0.92

MEMORY_CARE_TYPES = {
    "MEMORY_CARE_DEDICATED_HOME",
    "MEMORY_CARE_DEDICATED_LARGE",
    "ASSISTED_LIVING_WITH_MEMORY_CARE",
}
ASSISTED_LIVING_TYPES = {
    "ASSISTED_LIVING_COMMUNITY",
    "ASSISTED_LIVING_WITH_MEMORY_CARE",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_cms_certified(facility: Facility) -> bool:
    """A numeric CCN means Medicare certification; NV- prefixed ids are state-only."""
    return str(facility.cms_id or "").strip().isdigit()


def _license_signals(records: List[FacilityLicenseRecord]) -> Tuple[set, set]:
    care_types = set()
    endorsements = set()
    for record in records:
        if record.state_care_type:
            care_types.add(record.state_care_type.strip().upper())
        for item in str(record.state_endorsements or "").split(","):
            token = item.strip().upper()
            if token and token != "N/A":
                endorsements.add(token)
    return care_types, endorsements


def derivable_answers(
    facility: Facility,
    license_records: Optional[List[FacilityLicenseRecord]] = None,
) -> Dict[str, Tuple[str, str, float, str]]:
    """capability -> (answer, source, confidence, why).

    The rationale travels with the answer so a provider who disagrees can see what we read
    rather than being told the system decided.
    """
    answers: Dict[str, Tuple[str, str, float, str]] = {}
    care_types, endorsements = _license_signals(license_records or [])

    if _is_cms_certified(facility):
        answers["continuum_skilled_nursing"] = (
            AnswerState.YES.value,
            CMS_CERTIFICATION,
            CERTIFICATION_CONFIDENCE,
            "Medicare-certified skilled nursing facility (CCN on file).",
        )
        answers["medical_24_7_nursing"] = (
            AnswerState.YES.value,
            CMS_CERTIFICATION,
            CERTIFICATION_CONFIDENCE,
            "Federal participation requirements oblige a certified nursing facility to "
            "provide licensed nursing services 24 hours a day.",
        )
        answers["medical_physician_availability"] = (
            AnswerState.YES.value,
            CMS_CERTIFICATION,
            CERTIFICATION_CONFIDENCE,
            "Federal participation requirements oblige a certified nursing facility to "
            "have each resident supervised by a physician, with a physician available for "
            "emergencies.",
        )
        answers["accessibility_wheelchair_access"] = (
            AnswerState.YES.value,
            CMS_CERTIFICATION,
            CERTIFICATION_CONFIDENCE,
            "Accessibility is a condition of federal certification and of the Americans "
            "with Disabilities Act.",
        )

    if "SKILLED_NURSING" in care_types:
        answers.setdefault(
            "continuum_skilled_nursing",
            (
                AnswerState.YES.value,
                STATE_LICENSE,
                LICENSE_CONFIDENCE,
                "Licensed by Nevada as a skilled nursing facility.",
            ),
        )

    memory_care = bool(care_types & MEMORY_CARE_TYPES) or "ALZHEIMER DISEASE" in endorsements
    if memory_care:
        why = (
            "Nevada endorses this community for Alzheimer disease."
            if "ALZHEIMER DISEASE" in endorsements
            else "Licensed by Nevada under a dedicated memory care category."
        )
        answers["medical_memory_care"] = (AnswerState.YES.value, STATE_LICENSE, LICENSE_CONFIDENCE, why)
        answers["continuum_memory_care"] = (AnswerState.YES.value, STATE_LICENSE, LICENSE_CONFIDENCE, why)

    if bool(care_types & ASSISTED_LIVING_TYPES) or "ASSISTED LIVING SERVICES" in endorsements:
        answers["continuum_assisted_living"] = (
            AnswerState.YES.value,
            STATE_LICENSE,
            LICENSE_CONFIDENCE,
            "Nevada endorses this community to provide assisted living services."
            if "ASSISTED LIVING SERVICES" in endorsements
            else "Licensed by Nevada as an assisted living community.",
        )

    return answers


def apply_derived_capabilities(db: Session, facility_id: int) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).one_or_none()
    if facility is None:
        raise ValueError(f"Facility {facility_id} was not found.")

    records = (
        db.query(FacilityLicenseRecord)
        .filter(FacilityLicenseRecord.facility_id == facility_id)
        .all()
    )
    derived = derivable_answers(facility, records)
    if not derived:
        return {"facility_id": facility_id, "written": 0, "skipped_provider_answered": 0, "unchanged": 0}

    existing = {
        row.capability: row
        for row in db.query(FacilityCapability).filter(
            FacilityCapability.facility_id == facility_id,
            FacilityCapability.capability.in_(list(derived.keys())),
        )
    }

    written = 0
    skipped = 0
    unchanged = 0
    now = _now()
    for capability, (value, source, confidence, why) in derived.items():
        row = existing.get(capability)
        if row is not None and row.source == PORTAL_SOURCE:
            # The operator has spoken about this. Their answer stands.
            skipped += 1
            continue
        if row is not None and row.value.value == value and row.source == source:
            unchanged += 1
            continue
        if row is None:
            row = FacilityCapability(facility_id=facility_id, capability=capability)
            db.add(row)
        row.value = AnswerState(value)
        row.source = source
        row.confidence = confidence
        row.notes = why
        row.verified_at = now
        written += 1

    db.commit()
    return {
        "facility_id": facility_id,
        "written": written,
        "skipped_provider_answered": skipped,
        "unchanged": unchanged,
    }


def backfill_derived_capabilities(db: Session, limit: Optional[int] = None) -> Dict[str, int]:
    query = db.query(Facility.id).order_by(Facility.id)
    if limit:
        query = query.limit(limit)

    totals = {"facilities": 0, "written": 0, "skipped_provider_answered": 0, "unchanged": 0}
    for (facility_id,) in query.all():
        result = apply_derived_capabilities(db, facility_id)
        totals["facilities"] += 1
        totals["written"] += int(result["written"])
        totals["skipped_provider_answered"] += int(result["skipped_provider_answered"])
        totals["unchanged"] += int(result["unchanged"])
    return totals
