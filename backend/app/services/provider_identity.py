from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import (
    Facility,
    FacilityAuditLog,
    FacilityDomainAllowlist,
    FacilityLicenseRecord,
    FacilityUser,
    ProviderIdentityChallenge,
)

PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
}

ROLE_OWNER = "OWNER"
ROLE_ADMIN = "ADMIN"
ROLE_ADMISSIONS = "ADMISSIONS"
ROLE_MARKETING = "MARKETING"
ROLE_ACTIVITIES = "ACTIVITIES"
ROLE_CLINICAL_DIRECTOR = "CLINICAL_DIRECTOR"

ROLE_SET = {
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_ADMISSIONS,
    ROLE_MARKETING,
    ROLE_ACTIVITIES,
    ROLE_CLINICAL_DIRECTOR,
}

CATEGORY_MEDICAL = "MEDICAL"
CATEGORY_ACTIVITIES = "ACTIVITIES"
CATEGORY_PHOTOS = "PHOTOS"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_role(role: str) -> str:
    normalized = str(role or "").strip().upper()
    if normalized not in ROLE_SET:
        raise ValueError(f"Unsupported role: {role}")
    return normalized


def _email_domain(email: str) -> str:
    value = str(email or "").strip().lower()
    if "@" not in value:
        return ""
    return value.split("@", 1)[1]


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _is_domain_allowed(db: Session, facility_id: int, domain: str) -> bool:
    row = (
        db.query(FacilityDomainAllowlist)
        .filter(
            FacilityDomainAllowlist.facility_id == facility_id,
            FacilityDomainAllowlist.domain == domain,
            FacilityDomainAllowlist.is_active.is_(True),
        )
        .first()
    )
    return row is not None


def ensure_default_domain_allowlist(db: Session, facility: Facility) -> None:
    primary_domain = ""
    if facility.name:
        compact = "".join(ch for ch in facility.name.lower() if ch.isalnum() or ch == " ").strip().replace(" ", "")
        if compact:
            primary_domain = f"{compact}.org"

    if not primary_domain:
        return

    exists = (
        db.query(FacilityDomainAllowlist)
        .filter(
            FacilityDomainAllowlist.facility_id == facility.id,
            FacilityDomainAllowlist.domain == primary_domain,
        )
        .first()
    )
    if exists:
        return

    db.add(
        FacilityDomainAllowlist(
            facility_id=facility.id,
            domain=primary_domain,
            is_parent_org=False,
            is_active=True,
            manual_approval_required=False,
        )
    )
    db.commit()


def start_email_verification(
    db: Session,
    facility_id: int,
    email: str,
    full_name: Optional[str],
    role: str,
    ip_address: Optional[str],
) -> Dict[str, object]:
    role = _normalize_role(role)
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise ValueError("Facility not found")

    ensure_default_domain_allowlist(db, facility)

    domain = _email_domain(email)
    if not domain:
        raise ValueError("Invalid email format")

    if domain in PUBLIC_EMAIL_DOMAINS:
        raise ValueError("Public email domain requires manual approval")

    if not _is_domain_allowed(db, facility_id, domain):
        raise ValueError("Email domain is not allowed for this facility")

    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.facility_id == facility_id, FacilityUser.email == email)
        .first()
    )
    if user is None:
        user = FacilityUser(
            facility_id=facility_id,
            email=email,
            password_hash="PENDING_VERIFICATION",
            full_name=full_name,
            role=role,
            is_active=False,
            is_verified=False,
            verified_badge=False,
            verification_method="EMAIL_OTP",
            verification_sent_at=_now(),
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name or user.full_name
        user.role = role
        user.is_active = False
        user.is_verified = False
        user.verified_badge = False
        user.verification_method = "EMAIL_OTP"
        user.verification_sent_at = _now()

    code = f"{secrets.randbelow(1000000):06d}"
    challenge = ProviderIdentityChallenge(
        facility_id=facility_id,
        user_id=user.id,
        email=email,
        code_hash=_hash_code(code),
        verification_method="EMAIL_OTP",
        verification_sent_at=_now(),
        expires_at=_now() + timedelta(minutes=15),
        status="PENDING",
        attempt_count=0,
        ip_address=ip_address,
    )
    db.add(challenge)
    db.commit()

    return {
        "facility_id": facility_id,
        "user_id": user.id,
        "email": email,
        "verification_sent_at": challenge.verification_sent_at.isoformat(),
        "verification_method": "EMAIL_OTP",
        "debug_verification_code": code,
    }


def complete_email_verification(db: Session, facility_id: int, email: str, code: str) -> Dict[str, object]:
    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.facility_id == facility_id, FacilityUser.email == email)
        .first()
    )
    if not user:
        raise ValueError("User not found")

    challenge = (
        db.query(ProviderIdentityChallenge)
        .filter(
            ProviderIdentityChallenge.facility_id == facility_id,
            ProviderIdentityChallenge.user_id == user.id,
            ProviderIdentityChallenge.status == "PENDING",
        )
        .order_by(ProviderIdentityChallenge.id.desc())
        .first()
    )
    if not challenge:
        raise ValueError("No active verification challenge")

    now = _now()
    if _to_utc(challenge.expires_at) < now:
        challenge.status = "EXPIRED"
        db.commit()
        raise ValueError("Verification code expired")

    challenge.attempt_count = int(challenge.attempt_count or 0) + 1
    if challenge.code_hash != _hash_code(code):
        db.commit()
        raise ValueError("Invalid verification code")

    challenge.status = "COMPLETED"
    challenge.verification_completed_at = now

    user.is_active = True
    user.is_verified = True
    user.verified_badge = True
    user.verification_completed_at = now
    user.next_reverification_due_at = now + timedelta(days=365)

    db.commit()

    return {
        "facility_id": facility_id,
        "user_id": user.id,
        "verification_completed_at": now.isoformat(),
        "verification_method": user.verification_method,
    }


def validate_license_ownership(
    db: Session,
    facility_id: int,
    cms_provider_id: Optional[str],
    ahca_license_number: Optional[str],
    medicare_provider_number: Optional[str],
    legal_name: Optional[str],
    legal_address: Optional[str],
    domain: Optional[str],
) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise ValueError("Facility not found")

    name_match = bool(legal_name and str(legal_name).strip().lower() in str(facility.name or "").strip().lower())
    address_match = bool(legal_address and str(facility.address or "").strip().lower() in str(legal_address).strip().lower() or str(legal_address or "").strip().lower() in str(facility.address or "").strip().lower())

    normalized_domain = (domain or "").strip().lower()
    domain_allowed = False
    if normalized_domain:
        domain_allowed = _is_domain_allowed(db, facility_id, normalized_domain)

    provider_match = bool(cms_provider_id and str(cms_provider_id).strip() == str(facility.cms_id or "").strip())
    status = "VERIFIED" if (name_match and address_match and (domain_allowed or provider_match)) else "MISMATCH"

    record = FacilityLicenseRecord(
        facility_id=facility_id,
        cms_provider_id=cms_provider_id,
        ahca_license_number=ahca_license_number,
        medicare_provider_number=medicare_provider_number,
        legal_name=legal_name,
        legal_address=legal_address,
        domain=normalized_domain or None,
        status=status,
        verified_at=_now() if status == "VERIFIED" else None,
        verification_notes=f"name_match={name_match}; address_match={address_match}; domain_allowed={domain_allowed}; provider_match={provider_match}",
    )
    db.add(record)
    db.commit()

    return {
        "facility_id": facility_id,
        "status": status,
        "name_match": name_match,
        "address_match": address_match,
        "domain_allowed": domain_allowed,
        "provider_match": provider_match,
    }


def role_can_edit_category(role: str, category: str) -> bool:
    role = _normalize_role(role)
    category = str(category or "").strip().upper()

    if role in {ROLE_OWNER, ROLE_ADMIN}:
        return True

    if category == CATEGORY_MEDICAL:
        return role == ROLE_CLINICAL_DIRECTOR
    if category == CATEGORY_ACTIVITIES:
        return role == ROLE_ACTIVITIES
    if category == CATEGORY_PHOTOS:
        return role == ROLE_MARKETING
    return False


def _get_user(db: Session, facility_id: int, user_id: int) -> FacilityUser:
    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.id == user_id, FacilityUser.facility_id == facility_id)
        .first()
    )
    if not user:
        raise ValueError("User not found")
    return user


def apply_facility_field_update(
    db: Session,
    facility_id: int,
    user_id: int,
    field_name: str,
    new_value: Optional[str],
    category: str,
    ip_address: Optional[str],
) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise ValueError("Facility not found")

    user = _get_user(db, facility_id, user_id)
    if not role_can_edit_category(user.role, category):
        raise PermissionError("Role is not allowed to modify this category")

    if not hasattr(facility, field_name):
        raise ValueError("Unsupported field")

    old_value = getattr(facility, field_name)
    setattr(facility, field_name, new_value)

    log = FacilityAuditLog(
        facility_id=facility_id,
        user_id=user.id,
        field_name=field_name,
        old_value=None if old_value is None else str(old_value),
        new_value=None if new_value is None else str(new_value),
        user_role=user.role,
        ip_address=ip_address,
        is_reverted=False,
    )
    db.add(log)
    db.commit()

    return {
        "facility_id": facility_id,
        "audit_id": log.id,
        "field_name": field_name,
        "old_value": log.old_value,
        "new_value": log.new_value,
    }


def revert_audit_change(
    db: Session,
    facility_id: int,
    audit_id: int,
    reverted_by_user_id: int,
    ip_address: Optional[str],
) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise ValueError("Facility not found")

    actor = _get_user(db, facility_id, reverted_by_user_id)
    if _normalize_role(actor.role) not in {ROLE_OWNER, ROLE_ADMIN}:
        raise PermissionError("Only OWNER or ADMIN can revert changes")

    log = (
        db.query(FacilityAuditLog)
        .filter(FacilityAuditLog.id == audit_id, FacilityAuditLog.facility_id == facility_id)
        .first()
    )
    if not log:
        raise ValueError("Audit log not found")
    if log.is_reverted:
        raise ValueError("Audit log already reverted")

    if not hasattr(facility, log.field_name):
        raise ValueError("Field no longer exists")

    setattr(facility, log.field_name, log.old_value)
    log.is_reverted = True
    log.reverted_at = _now()
    log.reverted_by_user_id = actor.id

    reversal_log = FacilityAuditLog(
        facility_id=facility_id,
        user_id=actor.id,
        field_name=log.field_name,
        old_value=log.new_value,
        new_value=log.old_value,
        user_role=actor.role,
        ip_address=ip_address,
        is_reverted=False,
    )
    db.add(reversal_log)
    db.commit()

    return {
        "facility_id": facility_id,
        "reverted_audit_id": log.id,
        "reversal_audit_id": reversal_log.id,
    }


def invite_staff_member(
    db: Session,
    facility_id: int,
    inviter_user_id: int,
    email: str,
    full_name: Optional[str],
    role: str,
    ip_address: Optional[str],
) -> Dict[str, object]:
    inviter = _get_user(db, facility_id, inviter_user_id)
    if _normalize_role(inviter.role) not in {ROLE_OWNER, ROLE_ADMIN}:
        raise PermissionError("Only OWNER or ADMIN can invite staff")

    return start_email_verification(
        db=db,
        facility_id=facility_id,
        email=email,
        full_name=full_name,
        role=role,
        ip_address=ip_address,
    )


def request_role_change(
    db: Session,
    facility_id: int,
    actor_user_id: int,
    target_user_id: int,
    new_role: str,
) -> Dict[str, object]:
    actor = _get_user(db, facility_id, actor_user_id)
    target = _get_user(db, facility_id, target_user_id)
    new_role = _normalize_role(new_role)

    actor_role = _normalize_role(actor.role)
    if actor_role not in {ROLE_OWNER, ROLE_ADMIN}:
        raise PermissionError("Role escalation denied")

    if new_role == ROLE_OWNER and actor_role != ROLE_OWNER:
        raise PermissionError("Only OWNER can assign OWNER role")

    previous = target.role
    target.role = new_role
    db.commit()

    return {
        "facility_id": facility_id,
        "target_user_id": target.id,
        "old_role": previous,
        "new_role": new_role,
    }


def run_annual_reverification(db: Session) -> Dict[str, object]:
    now = _now()
    affected = 0

    users = db.query(FacilityUser).filter(FacilityUser.is_verified.is_(True)).all()
    for user in users:
        if user.next_reverification_due_at and _to_utc(user.next_reverification_due_at) < now:
            user.verified_badge = False
            user.is_verified = False
            user.is_active = False
            affected += 1

            facility = db.query(Facility).filter(Facility.id == user.facility_id).first()
            if facility:
                facility.confidence_level = "LOW"

    db.commit()
    return {"reverification_required_users": affected}
