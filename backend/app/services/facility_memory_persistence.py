from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import (
    AnswerState,
    FacilityVerificationMemory,
    FacilityVerificationRequest,
    FacilityVerificationResponse,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_state(value: str) -> AnswerState:
    normalized = str(value or "").strip().upper()
    if normalized in {"YES", "NO", "UNKNOWN", "LIMITED"}:
        return AnswerState(normalized)
    raise ValueError(f"Invalid answer state: {value}")


def _capability_ttl_days(capability_key: str) -> int:
    text = str(capability_key or "").strip().lower()

    if any(token in text for token in ["price", "pricing", "cost", "rate", "fee", "monthly_cost"]):
        return 30
    if any(token in text for token in ["activity", "movie", "music", "social", "garden", "exercise", "religious"]):
        return 30
    if any(token in text for token in ["meal", "dining", "diet", "gluten", "kosher", "food"]):
        return 180
    if any(token in text for token in ["therapy", "speech", "occupational", "physical", "rehab", "swallow"]):
        return 365
    if any(token in text for token in ["access", "walker", "wheelchair", "apartment", "pool", "fitness", "transport", "continuum", "feature"]):
        return 365
    return 365


def _confidence_score(
    state: AnswerState,
    verified_at: datetime,
    expires_at: datetime,
    verification_count: int,
    conflict_count: int,
) -> float:
    verified_at = _to_utc(verified_at)
    expires_at = _to_utc(expires_at)
    base = 82.0 if state in {AnswerState.YES, AnswerState.NO} else 70.0 if state == AnswerState.LIMITED else 50.0
    volume_bonus = min(12.0, max(0.0, (verification_count - 1) * 2.0))
    recency_days = max(0.0, (_utc_now() - verified_at).total_seconds() / 86400.0)
    recency_penalty = min(10.0, recency_days / 30.0)
    expired_penalty = 15.0 if _utc_now() > expires_at else 0.0
    conflict_penalty = min(25.0, conflict_count * 8.0)
    return round(max(0.0, min(100.0, base + volume_bonus - recency_penalty - expired_penalty - conflict_penalty)), 2)


def _provider_vs_family_conflict(db: Session, facility_id: int, capability_key: str) -> bool:
    no_count = (
        db.query(FacilityVerificationResponse)
        .filter(
            FacilityVerificationResponse.facility_id == facility_id,
            FacilityVerificationResponse.capability == capability_key,
            FacilityVerificationResponse.source == "FAMILY_REPORT",
            FacilityVerificationResponse.value == AnswerState.NO,
        )
        .count()
    )
    return no_count >= 3


def apply_provider_verification_answers(
    db: Session,
    facility_id: int,
    answers: List[Dict[str, str]],
    verified_by_user_id: Optional[int] = None,
    verification_method: str = "provider_portal",
    request_subject: Optional[str] = None,
    request_body: Optional[str] = None,
) -> Dict[str, object]:
    now = _utc_now()

    request = FacilityVerificationRequest(
        facility_id=facility_id,
        requested_by_user_id=verified_by_user_id,
        channel="provider_portal",
        subject=request_subject,
        body=request_body,
        status="answered",
        sent_at=now,
    )
    db.add(request)
    db.flush()

    persisted = 0
    conflicts = 0

    for answer in answers:
        capability_key = str(answer.get("capability_key") or "").strip()
        if not capability_key:
            continue

        value = _normalize_state(str(answer.get("value") or "UNKNOWN"))
        source = str(answer.get("source") or "PROVIDER_PORTAL").strip().upper() or "PROVIDER_PORTAL"
        verified_at = now
        ttl_days = _capability_ttl_days(capability_key)
        expires_at = verified_at + timedelta(days=ttl_days)

        response = FacilityVerificationResponse(
            request_id=request.id,
            facility_id=facility_id,
            responded_by_user_id=verified_by_user_id,
            capability=capability_key,
            value=value,
            source=source,
            verified_at=verified_at,
            expires_at=expires_at,
            confidence=0.0,
            notes=f"verification_method={verification_method}",
        )
        db.add(response)
        db.flush()

        memory = (
            db.query(FacilityVerificationMemory)
            .filter(
                FacilityVerificationMemory.facility_id == facility_id,
                FacilityVerificationMemory.capability == capability_key,
            )
            .first()
        )

        conflict_count = 0
        verification_count = 1

        if memory is not None:
            conflict_count = int(memory.conflict_count or 0)
            verification_count = int(memory.verification_count or 0) + 1

            if memory.value != value and memory.value != AnswerState.UNKNOWN and value != AnswerState.UNKNOWN:
                conflict_count += 1

        if value == AnswerState.YES and _provider_vs_family_conflict(db, facility_id, capability_key):
            conflict_count += 1

        confidence = _confidence_score(value, verified_at, expires_at, verification_count, conflict_count)
        response.confidence = confidence

        if memory is None:
            memory = FacilityVerificationMemory(
                facility_id=facility_id,
                capability=capability_key,
                value=value,
                verification_source=source,
                verified_at=verified_at,
                expires_at=expires_at,
                confidence=confidence,
                verification_count=verification_count,
                conflict_count=conflict_count,
                last_request_id=request.id,
                last_response_id=response.id,
            )
            db.add(memory)
        else:
            memory.value = value
            memory.verification_source = source
            memory.verified_at = verified_at
            memory.expires_at = expires_at
            memory.confidence = confidence
            memory.verification_count = verification_count
            memory.conflict_count = conflict_count
            memory.last_request_id = request.id
            memory.last_response_id = response.id

        if conflict_count > 0:
            conflicts += 1

        persisted += 1

    db.commit()

    return {
        "facility_id": facility_id,
        "request_id": request.id,
        "persisted_answers": persisted,
        "conflict_records": conflicts,
    }


def facility_memory_overlay(db: Session, facility_id: int) -> Dict[str, object]:
    now = _utc_now()
    rows = (
        db.query(FacilityVerificationMemory)
        .filter(FacilityVerificationMemory.facility_id == facility_id)
        .all()
    )

    capabilities: List[Dict[str, object]] = []
    confidences: List[float] = []

    for row in rows:
        expires_at = _to_utc(row.expires_at)
        is_expired = now > expires_at
        effective_confidence = float(row.confidence or 0.0)
        if is_expired:
            effective_confidence = max(0.0, effective_confidence - 15.0)

        capabilities.append(
            {
                "capability_key": row.capability,
                "value": row.value.value if hasattr(row.value, "value") else str(row.value),
                "source": row.verification_source,
                "verified_at": row.verified_at.isoformat() if row.verified_at else "",
                "expires_at": row.expires_at.isoformat() if row.expires_at else "",
                "expired": is_expired,
                "confidence": round(effective_confidence, 2),
                "verification_count": int(row.verification_count or 0),
                "conflict_count": int(row.conflict_count or 0),
                "status": "CONFLICT_REVIEW_REQUIRED" if int(row.conflict_count or 0) > 0 else "OK",
            }
        )
        confidences.append(effective_confidence)

    overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return {
        "facility_id": facility_id,
        "overall_confidence": overall_confidence,
        "capabilities": capabilities,
    }
