"""Email notices for the Israeli inquiry and visit flow.

Who hears what:
- Facility: new inquiry, family reply, visit requested / booked / accepted / cancelled by the family.
- Family (only if it left an email): its private link right after sending the inquiry, and
  facility answers, visit confirmed / proposed / cancelled by the facility, booking confirmation.

Rules:
- The family's private link is never stored in plain text, so only the emails sent while the
  family itself acts (it holds the token then) carry the link. Others say "open the link from
  the first email".
- Facility emails carry no family phone or email; the facility sees those in its portal.
- Synthetic facilities are never emailed. For testing, OOMNIK_NOTIFY_SYNTHETIC_TO redirects
  their facility notices to one address.
- Sending never blocks or fails the family's or facility's action: it runs in a background
  thread (OOMNIK_NOTIFY_SYNC=1 runs inline, for tests) and the outcome is recorded.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityInquiry, FacilityMarketRegistration, FacilityNotification, FacilityPortalInvite

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INTERNAL_DOMAINS = ("portal-invite.oomnik",)

FACILITY_EVENTS = {
    "NEW_INQUIRY": ("פנייה חדשה ממשפחה", "משפחה פנתה אליכם דרך OOMNIK."),
    "FAMILY_REPLY": ("המשפחה ענתה", "המשפחה כתבה תשובה בפנייה."),
    "VISIT_REQUESTED": ("בקשה לתיאום ביקור", "המשפחה הציעה מועדים לביקור ומחכה שתבחרו אחד."),
    "VISIT_BOOKED": ("נקבע ביקור", "המשפחה קבעה ביקור מתוך שעות הביקור שפרסמתם."),
    "VISIT_ACCEPTED": ("המשפחה אישרה את המועד", "המשפחה אישרה את המועד שהצעתם. הביקור נקבע."),
    "VISIT_CANCELLED": ("המשפחה ביטלה את הביקור", "המשפחה ביטלה את הביקור."),
}
FAMILY_EVENTS = {
    "INQUIRY_SENT": ("הפנייה נשלחה", "הפנייה שלכם נשלחה. כאן תוכלו לעקוב אחרי תשובת המוסד ולתאם ביקור."),
    "FACILITY_REPLY": ("המוסד ענה לפנייה", "המוסד ענה לפנייה שלכם."),
    "VISIT_CONFIRMED": ("הביקור אושר", "המוסד אישר את הביקור."),
    "VISIT_PROPOSED": ("המוסד הציע מועד לביקור", "המוסד הציע מועד אחר לביקור, ומחכה לאישור שלכם."),
    "VISIT_CANCELLED": ("המוסד ביטל את הביקור", "המוסד ביטל את הביקור. אפשר לקבוע מועד חדש."),
    "VISIT_BOOKED": ("הביקור נקבע", "הביקור שקבעתם נשמר."),
}


def _public_url() -> str:
    return os.getenv("OOMNIK_PUBLIC_URL", "https://www.oomnik.co.il").rstrip("/")


def valid_email(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text or len(text) > 254 or not _EMAIL_RE.match(text) or text.endswith(_INTERNAL_DOMAINS):
        return None
    return text


def facility_addresses(db: Session, facility: Facility) -> List[str]:
    found: List[str] = []
    row = (
        db.query(FacilityMarketRegistration)
        .filter(FacilityMarketRegistration.facility_id == facility.id, FacilityMarketRegistration.market == "israel")
        .one_or_none()
    )
    if row is not None:
        questionnaire = (json.loads(row.payload_json) or {}).get("questionnaire") or {}
        found.append(questionnaire.get("contact_email"))
    for (email,) in db.query(FacilityPortalInvite.contact_email).filter(
        FacilityPortalInvite.facility_id == facility.id, FacilityPortalInvite.revoked_at.is_(None)
    ):
        found.append(email)
    return list(dict.fromkeys(e for e in (valid_email(x) for x in found) if e))


def _is_synthetic(facility: Facility) -> bool:
    return str(facility.cms_id or "").upper().startswith("IL-SYN")


def _compose(audience: str, event: str, facility: Facility, inquiry: FacilityInquiry, *, visit: Optional[Dict[str, Any]], token: Optional[str]) -> Dict[str, str]:
    title, line = (FACILITY_EVENTS if audience == "FACILITY" else FAMILY_EVENTS)[event]
    name = facility.name or "המוסד"
    lines = [line]
    if visit and visit.get("date"):
        when = f"{visit.get('date_label') or visit['date']}, בשעה {visit.get('time')}" if visit.get("time") else (visit.get("date_label") or visit["date"])
        lines.append(f"מועד: {when}")
    if audience == "FACILITY":
        request = json.loads(inquiry.request_json or "{}")
        if request.get("contact_name"):
            lines.append(f"שם הפונה: {request['contact_name']}")
        lines.append(f"לפרטי הקשר ולתשובה, היכנסו לפורטל: {_public_url()}/provider/{facility.id}/israel")
        lines.append("אם לא נכנסתם לאחרונה, היכנסו דרך הקישור האישי שקיבלתם מ-OOMNIK.")
        subject = f"OOMNIK | {title} | פנייה #{inquiry.id}"
    else:
        if token:
            lines.append(f"הקישור האישי שלכם (שמרו אותו, הוא לא נשלח שוב): {_public_url()}/he/inquiry/{token}")
        else:
            lines.append("לפרטים, פתחו את הקישור האישי מהמייל הראשון שקיבלתם מ-OOMNIK.")
        subject = f"OOMNIK | {title} | {name}"
    lines.append("")
    lines.append("OOMNIK. מייל אוטומטי, אין צורך להשיב.")
    body = "\n".join(lines)
    html = '<div dir="rtl" style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6">' + "".join(
        f"<p>{_linkify(l)}</p>" if l else "" for l in lines
    ) + "</div>"
    return {"subject": subject, "body_text": body, "body_html": html}


def _linkify(text: str) -> str:
    from html import escape

    safe = escape(text)
    return re.sub(r"(https?://\S+)", r'<a href="\1">\1</a>', safe)


def _default_sender(*, subject: str, body_text: str, body_html: str, recipients: List[str]) -> tuple[bool, str]:
    from app.services.email_service import send_email_detailed

    result = send_email_detailed(subject=subject, body_text=body_text, body_html=body_html, recipients=recipients, max_retries=1)
    return result.ok, result.status if result.ok else f"{result.status}: {result.message}"[:300]


_sender: Callable[..., tuple[bool, str]] = _default_sender


def set_sender(sender: Optional[Callable[..., tuple[bool, str]]]) -> None:
    """Tests swap the transport; None restores SMTP."""
    global _sender
    _sender = sender or _default_sender


def _deliver(notification_id: int, message: Dict[str, str], recipients: List[str]) -> None:
    try:
        ok, detail = _sender(recipients=recipients, **message)
    except Exception as error:  # never let a notice break anything
        ok, detail = False, f"ERROR: {error}"[:300]
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(FacilityNotification).filter(FacilityNotification.id == notification_id).one_or_none()
        if row is not None:
            row.status = "SENT" if ok else "NOT_SENT"
            row.detail = detail
            db.commit()
    finally:
        db.close()
    if not ok:
        logger.warning("israel_notification_not_sent id=%s detail=%s", notification_id, detail)


def notify(
    db: Session,
    inquiry: FacilityInquiry,
    audience: str,
    event: str,
    *,
    visit: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
) -> Optional[int]:
    """Record and send one notice. Never raises."""
    try:
        facility = db.query(Facility).filter(Facility.id == inquiry.facility_id).one()
        if audience == "FACILITY":
            recipients = facility_addresses(db, facility)
            if _is_synthetic(facility):
                redirect = valid_email(os.getenv("OOMNIK_NOTIFY_SYNTHETIC_TO"))
                recipients = [redirect] if redirect else []
                skipped = None if redirect else "SKIPPED_SYNTHETIC"
            else:
                skipped = None if recipients else "SKIPPED_NO_ADDRESS"
        else:
            email = valid_email(json.loads(inquiry.request_json or "{}").get("contact_email"))
            recipients = [email] if email else []
            skipped = None if email else "SKIPPED_NO_ADDRESS"
        row = FacilityNotification(
            inquiry_id=inquiry.id, facility_id=facility.id, audience=audience, event=event, status=skipped or "QUEUED"
        )
        db.add(row)
        db.commit()
        if skipped:
            return row.id
        message = _compose(audience, event, facility, inquiry, visit=visit, token=token)
        if os.getenv("OOMNIK_NOTIFY_SYNC", "").strip() == "1":
            _deliver(row.id, message, recipients)
        else:
            threading.Thread(target=_deliver, args=(row.id, message, recipients), daemon=True).start()
        return row.id
    except Exception as error:
        logger.warning("israel_notification_failed event=%s error=%s", event, error)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def notification_summary(db: Session, inquiry_id: int, audience: str) -> List[Dict[str, Any]]:
    rows = (
        db.query(FacilityNotification)
        .filter(FacilityNotification.inquiry_id == inquiry_id, FacilityNotification.audience == audience)
        .order_by(FacilityNotification.id)
        .all()
    )
    return [{"event": r.event, "status": r.status} for r in rows]
