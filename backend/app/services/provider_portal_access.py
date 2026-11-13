"""Personal portal links and sessions for facilities.

Flow: OOMNIK creates an invite for a facility and sends it the link. Opening the link
redeems it for a session token that the browser keeps and sends as
``Authorization: Bearer <token>``. Provider write endpoints then take the acting user
from the session, never from the request body.

The link itself is the credential (owner decision, 2026-11-13: "the link of each
facility is sent to it"). Anyone holding it can act for the facility until it expires
or is revoked, so links are long, random, stored only as hashes, expire after 90 days,
and a new invite revokes the previous one.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.facility import (
    Facility,
    FacilityAuditLog,
    FacilityPortalInvite,
    FacilityPortalSession,
    FacilityUser,
)
from app.services.provider_identity import ROLE_OWNER

INVITE_TTL = timedelta(days=90)
SESSION_TTL = timedelta(days=30)
INVITE_USER_DOMAIN = "portal-invite.oomnik"


class PortalAuthError(Exception):
    """No valid session where one is required (maps to HTTP 401)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_required() -> bool:
    """Israel requires a portal session for provider writes; Nevada keeps the legacy
    body ``user_id`` until it gets the same treatment. Override with the env flag."""
    flag = os.getenv("OPTIME_PROVIDER_SESSION_REQUIRED", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    from app.services.market_scope import is_israel_market

    return is_israel_market()


def create_invite(db: Session, facility_id: int, contact_email: Optional[str] = None) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).one_or_none()
    if facility is None:
        raise ValueError(f"Facility {facility_id} was not found.")
    now = _now()
    for old in db.query(FacilityPortalInvite).filter(
        FacilityPortalInvite.facility_id == facility_id, FacilityPortalInvite.revoked_at.is_(None)
    ):
        old.revoked_at = now
    token = secrets.token_urlsafe(32)
    invite = FacilityPortalInvite(
        facility_id=facility_id,
        token_hash=_hash(token),
        contact_email=(contact_email or "").strip() or None,
        expires_at=now + INVITE_TTL,
        redeem_count=0,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {
        "invite_id": invite.id,
        "facility_id": facility_id,
        "canonical_id": facility.cms_id,
        "name": facility.name,
        "token": token,
        "expires_at": invite.expires_at.isoformat(),
    }


def revoke_invites(db: Session, facility_id: int) -> int:
    """Revoke the facility's links and every session opened from them."""
    now = _now()
    count = 0
    for invite in db.query(FacilityPortalInvite).filter(
        FacilityPortalInvite.facility_id == facility_id, FacilityPortalInvite.revoked_at.is_(None)
    ):
        invite.revoked_at = now
        count += 1
    for session in db.query(FacilityPortalSession).filter(
        FacilityPortalSession.facility_id == facility_id, FacilityPortalSession.revoked_at.is_(None)
    ):
        session.revoked_at = now
    db.commit()
    return count


def _invite_user(db: Session, invite: FacilityPortalInvite) -> FacilityUser:
    email = f"invite-{invite.facility_id}@{INVITE_USER_DOMAIN}"
    user = (
        db.query(FacilityUser)
        .filter(FacilityUser.facility_id == invite.facility_id, FacilityUser.email == email)
        .one_or_none()
    )
    if user is None:
        user = FacilityUser(
            facility_id=invite.facility_id,
            email=email,
            password_hash="!portal-invite",  # never a valid password hash
            full_name=invite.contact_email,
            role=ROLE_OWNER,
            is_active=True,
            is_verified=True,
            verification_method="PORTAL_INVITE_LINK",
        )
        db.add(user)
        db.flush()
    return user


def redeem_invite(db: Session, token: str, ip_address: Optional[str] = None) -> Dict[str, object]:
    invite = (
        db.query(FacilityPortalInvite)
        .filter(FacilityPortalInvite.token_hash == _hash(str(token or "")))
        .one_or_none()
    )
    now = _now()
    if invite is None or invite.revoked_at is not None or _aware(invite.expires_at) < now:
        raise PortalAuthError("הקישור אינו בתוקף. אפשר לבקש קישור חדש מ-OOMNIK.")

    user = _invite_user(db, invite)
    if not user.is_active:
        raise PortalAuthError("הגישה של המוסד הושבתה.")
    raw = secrets.token_urlsafe(32)
    db.add(
        FacilityPortalSession(
            token_hash=_hash(raw),
            facility_id=invite.facility_id,
            user_id=user.id,
            invite_id=invite.id,
            expires_at=now + SESSION_TTL,
        )
    )
    invite.first_redeemed_at = invite.first_redeemed_at or now
    invite.last_redeemed_at = now
    invite.redeem_count = (invite.redeem_count or 0) + 1
    user.last_login_at = now
    db.add(
        FacilityAuditLog(
            facility_id=invite.facility_id,
            user_id=user.id,
            field_name="portal:invite_redeemed",
            old_value=None,
            new_value=str(invite.id),
            ip_address=ip_address,
            user_role=user.role,
        )
    )
    db.commit()
    facility = db.query(Facility).filter(Facility.id == invite.facility_id).one()
    return {
        "session_token": raw,
        "facility_id": facility.id,
        "canonical_id": facility.cms_id,
        "name": facility.name,
        "user_id": user.id,
    }


def _bearer(authorization: Optional[str]) -> Optional[str]:
    value = str(authorization or "").strip()
    if value.lower().startswith("bearer "):
        token = value[7:].strip()
        return token or None
    return None


def session_from_header(db: Session, authorization: Optional[str]) -> Optional[FacilityPortalSession]:
    token = _bearer(authorization)
    if token is None:
        return None
    session = (
        db.query(FacilityPortalSession).filter(FacilityPortalSession.token_hash == _hash(token)).one_or_none()
    )
    if session is None or session.revoked_at is not None or _aware(session.expires_at) < _now():
        raise PortalAuthError("ההתחברות פגה. יש לפתוח שוב את הקישור האישי.")
    return session


def acting_user_id(
    db: Session,
    facility_id: int,
    authorization: Optional[str],
    body_user_id: Optional[int],
) -> Optional[int]:
    """The user a provider write acts as.

    A session always wins over the body and must belong to the facility in the URL.
    Without a session the legacy body ``user_id`` is accepted only where sessions are
    not required.
    """
    session = session_from_header(db, authorization)
    if session is not None:
        if session.facility_id != facility_id:
            raise PermissionError("ההתחברות שייכת למוסד אחר.")
        return int(session.user_id)
    if session_required():
        raise PortalAuthError("יש להיכנס דרך הקישור האישי של המוסד.")
    # Legacy path: unchanged behaviour, the downstream service validates the body value.
    return body_user_id


def describe_session(db: Session, authorization: Optional[str]) -> Tuple[FacilityPortalSession, Facility]:
    session = session_from_header(db, authorization)
    if session is None:
        raise PortalAuthError("יש להיכנס דרך הקישור האישי של המוסד.")
    facility = db.query(Facility).filter(Facility.id == session.facility_id).one()
    return session, facility
