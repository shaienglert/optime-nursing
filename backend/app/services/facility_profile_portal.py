"""Provider-facing profile completion.

The portal exists because of a gap the public record cannot close. CMS, state licensing
and inspection data describe a facility's regulatory history in detail and say almost
nothing about what living there is like. A daughter choosing for her mother asks whether
there is a garden, whether services are held on Saturday, whether the fitness room is
real. Those answers can only come from the provider.

Two rules from the wider product carry into every function here.

UNKNOWN is not a negative. An unanswered capability never ranks a facility down and is
never inferred to be NO -- but it also cannot match a family who asked for it. That
asymmetry is the whole incentive for a provider to fill the profile in, and it is stated
to them in exactly those terms rather than implied.

Provenance travels with the answer. A capability answered in the portal is recorded with
source="provider_portal" and the user who set it, so a downstream consumer can always
tell a provider's own claim apart from something read off a government file.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.facility import (
    AnswerState,
    Facility,
    FacilityActivityCategory,
    FacilityAuditLog,
    FacilityCapability,
    FacilityPhoto,
    FacilityProfileCompleteness,
    FacilityUser,
)
from app.models.facility_questionnaire import (
    ANSWER_STATES,
    FACILITY_QUESTIONNAIRE_V1,
    facility_questionnaire_v1_flat,
)
from app.services.provider_identity import (
    CATEGORY_ACTIVITIES,
    CATEGORY_MEDICAL,
    CATEGORY_PHOTOS,
    role_can_edit_category,
)

PORTAL_SOURCE = "provider_portal"

# Completeness is tracked in five buckets while the questionnaire has seven sections, so
# the mapping is explicit rather than derived. Rehabilitation, accessibility and the care
# continuum are all clinical questions and roll up with Medical; housing is part of how a
# resident actually lives and rolls up with Lifestyle.
SECTION_TO_BUCKET: Dict[str, str] = {
    "Medical": "medical",
    "Rehabilitation": "medical",
    "Accessibility": "medical",
    "Future Care Continuum": "medical",
    "Lifestyle": "lifestyle",
    "Housing": "lifestyle",
    "Dining": "dining",
}

# Which portal role may answer which section, expressed through the identity service's
# existing category vocabulary so there is one permission model rather than two.
SECTION_TO_EDIT_CATEGORY: Dict[str, str] = {
    "Medical": CATEGORY_MEDICAL,
    "Rehabilitation": CATEGORY_MEDICAL,
    "Accessibility": CATEGORY_MEDICAL,
    "Future Care Continuum": CATEGORY_MEDICAL,
    "Lifestyle": CATEGORY_ACTIVITIES,
    "Housing": CATEGORY_ACTIVITIES,
    "Dining": CATEGORY_ACTIVITIES,
}

# A profile with eight photographs is not twice as useful as one with four; the curve
# flattens quickly. Ten is treated as complete so the bar stays reachable.
PHOTO_TARGET = 10

_QUESTION_INDEX: Dict[str, Dict[str, str]] = {
    item["key"]: item for item in facility_questionnaire_v1_flat()
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_answer(value: str) -> str:
    answer = str(value or "").strip().upper()
    if answer not in ANSWER_STATES:
        raise ValueError(
            f"Unsupported answer '{value}'. Expected one of: {', '.join(ANSWER_STATES)}."
        )
    return answer


def _get_facility(db: Session, facility_id: int) -> Facility:
    facility = db.query(Facility).filter(Facility.id == facility_id).one_or_none()
    if facility is None:
        raise ValueError(f"Facility {facility_id} was not found.")
    return facility


def _get_user(db: Session, facility_id: int, user_id: int) -> FacilityUser:
    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.id == user_id, FacilityUser.facility_id == facility_id)
        .one_or_none()
    )
    if user is None:
        raise PermissionError("User does not belong to this facility.")
    if not user.is_active:
        raise PermissionError("User account is not active.")
    return user


def search_claimable_facilities(
    db: Session,
    query: str,
    state: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, object]]:
    """Find a facility by name so its operator can recognise it and claim it.

    Deliberately open: this runs before anyone has proved who they are, and everything it
    returns is already public record. Proving the claim is the identity service's job, not
    this one's -- gating search would only stop an operator finding their own listing.
    """
    term = str(query or "").strip()
    if len(term) < 2:
        return []

    rows = db.query(Facility).filter(Facility.name.ilike(f"%{term}%"))
    if state:
        rows = rows.filter(Facility.state == state.strip().upper())
    if city:
        rows = rows.filter(Facility.city.ilike(f"%{city.strip()}%"))

    bounded = max(1, min(int(limit), 100))
    results: List[Dict[str, object]] = []
    for facility in rows.order_by(Facility.name).limit(bounded).all():
        claimed = (
            db.query(sa_func.count(FacilityUser.id))
            .filter(FacilityUser.facility_id == facility.id, FacilityUser.is_verified.is_(True))
            .scalar()
            or 0
        )
        results.append(
            {
                "facility_id": facility.id,
                "cms_id": facility.cms_id,
                "name": facility.name,
                "address": facility.address,
                "city": facility.city,
                "state": facility.state,
                "zip_code": facility.zip_code,
                "beds": facility.beds,
                "overall_rating": facility.overall_rating,
                "already_claimed": bool(claimed),
            }
        )
    return results


def _known_from_public_record(facility: Facility) -> List[Dict[str, object]]:
    """What we already hold, so the provider corrects rather than starts from blank."""
    return [
        {"key": "name", "label": "Community name", "value": facility.name, "source": "CMS"},
        {"key": "address", "label": "Address", "value": facility.address, "source": "CMS"},
        {"key": "city", "label": "City", "value": facility.city, "source": "CMS"},
        {"key": "state", "label": "State", "value": facility.state, "source": "CMS"},
        {"key": "zip_code", "label": "ZIP", "value": facility.zip_code, "source": "CMS"},
        {"key": "phone", "label": "Phone", "value": facility.phone, "source": "CMS"},
        {"key": "beds", "label": "Certified beds", "value": facility.beds, "source": "CMS"},
        {
            "key": "overall_rating",
            "label": "CMS overall rating",
            "value": facility.overall_rating,
            "source": "CMS",
        },
        {
            "key": "staffing_rating",
            "label": "CMS staffing rating",
            "value": facility.staffing_rating,
            "source": "CMS",
        },
        {
            "key": "inspection_rating",
            "label": "CMS inspection rating",
            "value": facility.inspection_rating,
            "source": "CMS",
        },
    ]


def facility_profile_snapshot(db: Session, facility_id: int) -> Dict[str, object]:
    """Everything the editor needs in one read: what we know, what we're missing, and why it matters."""
    facility = _get_facility(db, facility_id)

    answers = {
        row.capability: row
        for row in db.query(FacilityCapability).filter(
            FacilityCapability.facility_id == facility_id
        )
    }

    sections: List[Dict[str, object]] = []
    for section, questions in FACILITY_QUESTIONNAIRE_V1.items():
        items: List[Dict[str, object]] = []
        for question in questions:
            existing = answers.get(question["key"])
            items.append(
                {
                    "key": question["key"],
                    "label": question["label"],
                    "value": existing.value.value if existing else AnswerState.UNKNOWN.value,
                    "source": existing.source if existing else None,
                    "updated_at": existing.updated_at.isoformat() if existing and existing.updated_at else None,
                }
            )
        answered = sum(1 for item in items if item["value"] != AnswerState.UNKNOWN.value)
        sections.append(
            {
                "section": section,
                "edit_category": SECTION_TO_EDIT_CATEGORY.get(section, CATEGORY_MEDICAL),
                "answered": answered,
                "total": len(items),
                "questions": items,
            }
        )

    photos = [
        {
            "id": photo.id,
            "category": photo.category,
            "url": photo.url,
            "caption": photo.caption,
            "source": photo.source,
            "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else None,
        }
        for photo in db.query(FacilityPhoto)
        .filter(FacilityPhoto.facility_id == facility_id, FacilityPhoto.is_active.is_(True))
        .order_by(FacilityPhoto.uploaded_at.desc())
        .all()
    ]

    activities = [
        {
            "category": row.category,
            "availability": row.availability.value,
            "confidence": row.confidence,
            "import_source": row.import_source,
            "last_imported_at": row.last_imported_at.isoformat() if row.last_imported_at else None,
        }
        for row in db.query(FacilityActivityCategory)
        .filter(FacilityActivityCategory.facility_id == facility_id)
        .order_by(FacilityActivityCategory.category)
        .all()
    ]

    return {
        "facility_id": facility.id,
        "name": facility.name,
        "known_from_public_record": _known_from_public_record(facility),
        "sections": sections,
        "photos": photos,
        "photo_target": PHOTO_TARGET,
        "activities": activities,
        "activity_calendar_connected": any(row["import_source"] for row in activities),
        "completeness": recompute_completeness(db, facility_id),
        "answer_states": list(ANSWER_STATES),
        "governance": {
            "unknownIsNotNegative": True,
            "unknownCannotMatch": True,
            "providerAnswersCarryProvenance": True,
        },
    }


def save_capabilities(
    db: Session,
    facility_id: int,
    user_id: int,
    answers: Dict[str, str],
    ip_address: Optional[str] = None,
) -> Dict[str, object]:
    """Upsert questionnaire answers, one audit row per actual change.

    Rejects the whole submission if the user may not edit one of the sections it touches,
    rather than silently saving the permitted half -- a provider who thinks they saved
    twenty answers and saved twelve has been told something untrue by the product.
    """
    _get_facility(db, facility_id)
    user = _get_user(db, facility_id, user_id)

    if not answers:
        return {"updated": 0, "unchanged": 0, "completeness": recompute_completeness(db, facility_id)}

    normalized: Dict[str, str] = {}
    for key, value in answers.items():
        question = _QUESTION_INDEX.get(key)
        if question is None:
            raise ValueError(f"Unknown capability '{key}'.")
        category = SECTION_TO_EDIT_CATEGORY.get(question["section"], CATEGORY_MEDICAL)
        if not role_can_edit_category(user.role, category):
            raise PermissionError(
                f"Role {user.role} may not answer {question['section']} questions."
            )
        normalized[key] = _normalize_answer(value)

    existing = {
        row.capability: row
        for row in db.query(FacilityCapability).filter(
            FacilityCapability.facility_id == facility_id,
            FacilityCapability.capability.in_(list(normalized.keys())),
        )
    }

    now = _now()
    updated = 0
    unchanged = 0
    for key, value in normalized.items():
        row = existing.get(key)
        previous = row.value.value if row else None
        if previous == value:
            unchanged += 1
            continue

        if row is None:
            row = FacilityCapability(facility_id=facility_id, capability=key)
            db.add(row)

        row.value = AnswerState(value)
        row.source = PORTAL_SOURCE
        row.last_updated_by_user_id = user.id
        row.verified_at = now
        row.verification_count = (row.verification_count or 0) + 1
        # A provider stating a fact about their own community is the strongest evidence
        # available for a lifestyle or dining question; it is still a claim, not an
        # inspection, so it stops short of certainty.
        row.confidence = 0.9

        db.add(
            FacilityAuditLog(
                facility_id=facility_id,
                user_id=user.id,
                field_name=f"capability:{key}",
                old_value=previous,
                new_value=value,
                ip_address=ip_address,
                user_role=user.role,
            )
        )
        updated += 1

    db.commit()
    return {
        "updated": updated,
        "unchanged": unchanged,
        "completeness": recompute_completeness(db, facility_id),
    }


def add_photo(
    db: Session,
    facility_id: int,
    user_id: int,
    category: str,
    url: str,
    caption: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Dict[str, object]:
    _get_facility(db, facility_id)
    user = _get_user(db, facility_id, user_id)
    if not role_can_edit_category(user.role, CATEGORY_PHOTOS):
        raise PermissionError(f"Role {user.role} may not manage photographs.")

    clean_url = str(url or "").strip()
    if not clean_url.lower().startswith(("http://", "https://")):
        raise ValueError("Photo URL must be an absolute http or https address.")
    clean_category = str(category or "").strip() or "general"

    photo = FacilityPhoto(
        facility_id=facility_id,
        category=clean_category,
        url=clean_url,
        caption=(str(caption).strip() or None) if caption else None,
        source=PORTAL_SOURCE,
        uploaded_by_user_id=user.id,
    )
    db.add(photo)
    db.add(
        FacilityAuditLog(
            facility_id=facility_id,
            user_id=user.id,
            field_name="photo:add",
            old_value=None,
            new_value=clean_url,
            ip_address=ip_address,
            user_role=user.role,
        )
    )
    db.commit()
    db.refresh(photo)
    return {
        "photo_id": photo.id,
        "category": photo.category,
        "url": photo.url,
        "caption": photo.caption,
        "completeness": recompute_completeness(db, facility_id),
    }


def deactivate_photo(
    db: Session,
    facility_id: int,
    user_id: int,
    photo_id: int,
    ip_address: Optional[str] = None,
) -> Dict[str, object]:
    """Soft delete. A removed photograph stays in the row so the audit trail survives it."""
    _get_facility(db, facility_id)
    user = _get_user(db, facility_id, user_id)
    if not role_can_edit_category(user.role, CATEGORY_PHOTOS):
        raise PermissionError(f"Role {user.role} may not manage photographs.")

    photo = (
        db.query(FacilityPhoto)
        .filter(FacilityPhoto.id == photo_id, FacilityPhoto.facility_id == facility_id)
        .one_or_none()
    )
    if photo is None:
        raise ValueError(f"Photo {photo_id} was not found for this facility.")

    photo.is_active = False
    db.add(
        FacilityAuditLog(
            facility_id=facility_id,
            user_id=user.id,
            field_name="photo:remove",
            old_value=photo.url,
            new_value=None,
            ip_address=ip_address,
            user_role=user.role,
        )
    )
    db.commit()
    return {"photo_id": photo_id, "removed": True, "completeness": recompute_completeness(db, facility_id)}


def _bucket_ratio(answers: Dict[str, FacilityCapability], keys: Sequence[str]) -> float:
    if not keys:
        return 0.0
    known = sum(
        1
        for key in keys
        if key in answers and answers[key].value != AnswerState.UNKNOWN
    )
    return round(known / len(keys), 4)


def recompute_completeness(db: Session, facility_id: int) -> Dict[str, object]:
    """Recalculate and persist the five completeness buckets.

    Reported back to the provider verbatim: this number is the argument for filling the
    profile in, so it has to be the same number the platform actually holds rather than a
    flattering approximation of it.
    """
    answers = {
        row.capability: row
        for row in db.query(FacilityCapability).filter(
            FacilityCapability.facility_id == facility_id
        )
    }

    bucket_keys: Dict[str, List[str]] = {"medical": [], "lifestyle": [], "dining": []}
    for section, questions in FACILITY_QUESTIONNAIRE_V1.items():
        bucket = SECTION_TO_BUCKET.get(section)
        if bucket is None:
            continue
        bucket_keys[bucket].extend(question["key"] for question in questions)

    medical = _bucket_ratio(answers, bucket_keys["medical"])
    lifestyle = _bucket_ratio(answers, bucket_keys["lifestyle"])
    dining = _bucket_ratio(answers, bucket_keys["dining"])

    photo_count = (
        db.query(sa_func.count(FacilityPhoto.id))
        .filter(FacilityPhoto.facility_id == facility_id, FacilityPhoto.is_active.is_(True))
        .scalar()
        or 0
    )
    photos = round(min(1.0, photo_count / PHOTO_TARGET), 4)

    activity_rows = (
        db.query(FacilityActivityCategory)
        .filter(FacilityActivityCategory.facility_id == facility_id)
        .all()
    )
    known_activities = [
        row for row in activity_rows if row.availability != AnswerState.UNKNOWN
    ]
    activity = round(min(1.0, len(known_activities) / 7), 4) if activity_rows else 0.0

    overall = round((medical + lifestyle + dining + photos + activity) / 5, 4)

    record = (
        db.query(FacilityProfileCompleteness)
        .filter(FacilityProfileCompleteness.facility_id == facility_id)
        .one_or_none()
    )
    if record is None:
        record = FacilityProfileCompleteness(facility_id=facility_id)
        db.add(record)

    record.medical_completeness = medical
    record.lifestyle_completeness = lifestyle
    record.dining_completeness = dining
    record.photos_completeness = photos
    record.activity_completeness = activity
    record.overall_score = overall
    record.calculated_at = _now()
    db.commit()

    unanswered = [
        key
        for key in _QUESTION_INDEX
        if key not in answers or answers[key].value == AnswerState.UNKNOWN
    ]
    return {
        "medical": medical,
        "lifestyle": lifestyle,
        "dining": dining,
        "photos": photos,
        "activity": activity,
        "overall": overall,
        "photo_count": int(photo_count),
        "photo_target": PHOTO_TARGET,
        "unanswered_count": len(unanswered),
        "total_questions": len(_QUESTION_INDEX),
    }
