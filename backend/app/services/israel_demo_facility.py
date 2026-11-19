"""Owner demo facility (owner 2026-11-19): one synthetic facility whose notices go to the
owner's own address, so the facility side can be experienced end to end.

OOMNIK_DEMO_FACILITY="IL-SYN-149=owner@example.com" (synthetic market only).
On startup the facility's contact email is set to that address and, unless a live portal
link for that address already exists, a new personal portal link is emailed to it.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityMarketRegistration, FacilityPortalInvite

logger = logging.getLogger(__name__)


def demo_setting() -> Optional[Tuple[str, str]]:
    from app.services.israel_notifications import valid_email

    raw = os.getenv("OOMNIK_DEMO_FACILITY", "").strip()
    if "=" not in raw:
        return None
    canonical_id, email = (part.strip() for part in raw.split("=", 1))
    email = valid_email(email)
    if not canonical_id.upper().startswith("IL-SYN") or not email:
        return None  # only a synthetic facility can be a demo facility
    return canonical_id, email


def is_demo_facility(facility: Facility) -> bool:
    setting = demo_setting()
    return bool(setting and str(facility.cms_id or "") == setting[0])


def _public_url() -> str:
    return os.getenv("OOMNIK_PUBLIC_URL", "https://www.oomnik.co.il").rstrip("/")


def ensure_demo_facility(db: Session) -> str:
    setting = demo_setting()
    if setting is None:
        return "NOT_CONFIGURED"
    canonical_id, email = setting
    facility = db.query(Facility).filter(Facility.cms_id == canonical_id).one_or_none()
    if facility is None:
        return "FACILITY_NOT_FOUND"
    row = (
        db.query(FacilityMarketRegistration)
        .filter(FacilityMarketRegistration.facility_id == facility.id, FacilityMarketRegistration.market == "israel")
        .one_or_none()
    )
    if row is not None:
        payload = json.loads(row.payload_json) or {}
        questionnaire = payload.setdefault("questionnaire", {})
        if questionnaire.get("contact_email") != email:
            questionnaire["contact_email"] = email
            row.payload_json = json.dumps(payload, ensure_ascii=False)
            db.commit()
    now = datetime.now(timezone.utc)
    for invite in db.query(FacilityPortalInvite).filter(
        FacilityPortalInvite.facility_id == facility.id,
        FacilityPortalInvite.revoked_at.is_(None),
        FacilityPortalInvite.contact_email == email,
    ):
        expires = invite.expires_at if invite.expires_at.tzinfo else invite.expires_at.replace(tzinfo=timezone.utc)
        if expires > now:
            return "LINK_ALREADY_SENT"

    from app.services.email_service import send_email_detailed
    from app.services.provider_portal_access import create_invite

    invite = create_invite(db, facility.id, email)
    link = f"{_public_url()}/he/portal/{invite['token']}"
    lines = [
        f"זה הקישור האישי לפורטל של מוסד ההדגמה: {facility.name}.",
        "בפורטל תראו פניות של משפחות, תענו להן, תאשרו ביקורים ותקבעו שעות ביקור.",
        f"קישור לפורטל: {link}",
        "הקישור אישי. אל תעבירו אותו הלאה.",
        "",
        "המוסד סינתטי: כל ההתראות שלו יגיעו לכתובת הזו.",
    ]
    result = send_email_detailed(
        subject=f"OOMNIK | קישור לפורטל של {facility.name}",
        body_text="\n".join(lines),
        body_html='<div dir="rtl" style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6">'
        + "".join(f"<p>{line}</p>" for line in lines if line).replace(link, f'<a href="{link}">{link}</a>')
        + "</div>",
        recipients=[email],
        max_retries=1,
    )
    if not result.ok:
        # Without the email the link is unreachable; revoke it so the next start retries.
        from app.services.provider_portal_access import revoke_invites

        revoke_invites(db, facility.id)
        logger.warning("israel_demo_facility_link_not_sent status=%s", result.status)
        return "LINK_NOT_SENT"
    return "LINK_SENT"
