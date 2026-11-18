"""Focused family-to-facility requests (owner spec, 2026-11-15).

A family that likes a facility sends a short request: room type, move-in timing and,
only if it chooses to share them, its monthly and deposit ceilings. The facility can
accept, propose another track, or ask for a missing detail. The family follows the
thread through a private link; the facility answers from its portal session.

Nothing here touches matching or ranking.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityAuditLog, FacilityInquiry, FacilityUser
from app.services.israel_facility_questionnaire import LEVEL_OPTIONS, ROOM_OPTIONS
from app.services.market_scope import ISRAEL_STATE_CODE

MOVE_IN_OPTIONS = {"ASAP": "בהקדם", "WITHIN_MONTH": "בתוך חודש", "WITHIN_3_MONTHS": "בתוך שלושה חודשים", "EXPLORING": "רק בודקים"}
RESPONSE_KINDS = {
    "ACCEPT": "המוסד מאשר שיש התאמה",
    "ALTERNATIVE": "המוסד מציע מסלול אחר",
    "NEED_INFO": "המוסד מבקש פרט נוסף",
    "DECLINE": "המוסד לא יכול לקבל כרגע",
}
STATUS_LABELS = {
    "SENT": "נשלחה, ממתינה לתשובת המוסד",
    "ACCEPT": RESPONSE_KINDS["ACCEPT"],
    "ALTERNATIVE": RESPONSE_KINDS["ALTERNATIVE"],
    "NEED_INFO": RESPONSE_KINDS["NEED_INFO"],
    "DECLINE": RESPONSE_KINDS["DECLINE"],
}
_PHONE_RE = re.compile(r"^[0-9+\-() ]{7,20}$")
MAX_TEXT = 1000


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(value: Any, label: str) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: סכום לא תקין.") from error
    if number < 0 or number > 50_000_000:
        raise ValueError(f"{label}: סכום לא תקין.")
    return number


def _text(value: Any, label: str, required: bool = False, limit: int = MAX_TEXT) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{label}: שדה חובה.")
        return None
    if len(text) > limit:
        raise ValueError(f"{label}: הטקסט ארוך מדי.")
    return text


def validate_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    rooms, levels = dict(ROOM_OPTIONS), dict(LEVEL_OPTIONS)
    room = str(payload.get("room_type") or "").upper() or None
    if room and room not in rooms:
        raise ValueError("סוג חדר לא מוכר.")
    level = str(payload.get("level") or "").upper() or None
    if level and level not in levels:
        raise ValueError("רמת טיפול לא מוכרת.")
    move_in = str(payload.get("move_in") or "").upper()
    if move_in not in MOVE_IN_OPTIONS:
        raise ValueError("יש לבחור מועד כניסה.")
    phone = _text(payload.get("contact_phone"), "טלפון", required=True, limit=20)
    if not _PHONE_RE.match(phone):
        raise ValueError("טלפון: מספר לא תקין.")
    return {
        "room_type": room,
        "level": level,
        "move_in": move_in,
        "monthly_cap_ils": _money(payload.get("monthly_cap_ils"), "תשלום חודשי"),
        "deposit_cap_ils": _money(payload.get("deposit_cap_ils"), "פיקדון"),
        "contact_name": _text(payload.get("contact_name"), "שם", required=True, limit=80),
        "contact_phone": phone,
        "contact_email": _email(payload.get("contact_email")),
        "note": _text(payload.get("note"), "הערה"),
    }


def _email(value: Any) -> Optional[str]:
    from app.services.israel_notifications import valid_email

    if not str(value or "").strip():
        return None
    email = valid_email(value)
    if email is None:
        raise ValueError("דוא\"ל: כתובת לא תקינה.")
    return email


def _israeli_facility(db: Session, canonical_id: str) -> Facility:
    facility = db.query(Facility).filter(Facility.cms_id == canonical_id).one_or_none()
    if facility is None or str(facility.state or "").upper() != ISRAEL_STATE_CODE:
        raise LookupError("Facility not found")
    return facility


def create_inquiry(db: Session, canonical_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    facility = _israeli_facility(db, canonical_id)
    request = validate_request(payload)
    token = secrets.token_urlsafe(24)
    inquiry = FacilityInquiry(
        facility_id=facility.id,
        token_hash=_hash(token),
        status="SENT",
        request_json=json.dumps(request, ensure_ascii=False),
        messages_json=json.dumps([{"from": "FAMILY", "kind": "REQUEST", "at": _now()}], ensure_ascii=False),
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    from app.services.israel_notifications import notify

    notify(db, inquiry, "FACILITY", "NEW_INQUIRY")
    notify(db, inquiry, "FAMILY", "INQUIRY_SENT", token=token)
    return {"inquiry_id": inquiry.id, "token": token, "link_path": f"/he/inquiry/{token}", "email_sent_to_family": bool(request.get("contact_email"))}


def _view(inquiry: FacilityInquiry, facility: Facility, *, for_facility: bool) -> Dict[str, Any]:
    request = json.loads(inquiry.request_json)
    rooms, levels = dict(ROOM_OPTIONS), dict(LEVEL_OPTIONS)
    shown = {
        "room_type": rooms.get(request.get("room_type"), "לא צוין"),
        "level": levels.get(request.get("level"), "לא צוין"),
        "move_in": MOVE_IN_OPTIONS[request["move_in"]],
        "monthly_cap_ils": request.get("monthly_cap_ils"),
        "deposit_cap_ils": request.get("deposit_cap_ils"),
        "note": request.get("note"),
    }
    if for_facility:
        # Contact details go only to the facility the family wrote to.
        shown["contact_name"] = request["contact_name"]
        shown["contact_phone"] = request["contact_phone"]
        shown["contact_email"] = request.get("contact_email")
    return {
        "inquiry_id": inquiry.id,
        "facility": {"canonical_id": facility.cms_id, "name": facility.name},
        "status": inquiry.status,
        "status_label": STATUS_LABELS.get(inquiry.status, inquiry.status),
        "request": shown,
        "messages": json.loads(inquiry.messages_json),
        "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
        "visit": _visit(inquiry),
    }


def _visit(inquiry: FacilityInquiry) -> Optional[Dict[str, Any]]:
    from sqlalchemy.orm import object_session

    from app.models.facility import FacilityVisit
    from app.services.israel_visits import visit_view

    session = object_session(inquiry)
    if session is None:
        return None
    return visit_view(session.query(FacilityVisit).filter(FacilityVisit.inquiry_id == inquiry.id).one_or_none())


def _by_token(db: Session, token: str) -> FacilityInquiry:
    inquiry = db.query(FacilityInquiry).filter(FacilityInquiry.token_hash == _hash(str(token or ""))).one_or_none()
    if inquiry is None:
        raise LookupError("Inquiry not found")
    return inquiry


def family_view(db: Session, token: str) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    facility = db.query(Facility).filter(Facility.id == inquiry.facility_id).one()
    return _view(inquiry, facility, for_facility=False)


def family_reply(db: Session, token: str, text: Any) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    message = _text(text, "תשובה", required=True)
    messages: List[Dict[str, Any]] = json.loads(inquiry.messages_json)
    messages.append({"from": "FAMILY", "kind": "REPLY", "text": message, "at": _now()})
    inquiry.messages_json = json.dumps(messages, ensure_ascii=False)
    inquiry.status = "SENT"
    db.commit()
    from app.services.israel_notifications import notify

    notify(db, inquiry, "FACILITY", "FAMILY_REPLY")
    return family_view(db, token)


def facility_list(db: Session, facility_id: int) -> List[Dict[str, Any]]:
    facility = db.query(Facility).filter(Facility.id == facility_id).one()
    rows = (
        db.query(FacilityInquiry)
        .filter(FacilityInquiry.facility_id == facility_id)
        .order_by(FacilityInquiry.created_at.desc(), FacilityInquiry.id.desc())
        .all()
    )
    return [_view(row, facility, for_facility=True) for row in rows]


def facility_respond(
    db: Session, facility_id: int, user_id: int, inquiry_id: int, payload: Dict[str, Any]
) -> Dict[str, Any]:
    inquiry = (
        db.query(FacilityInquiry)
        .filter(FacilityInquiry.id == inquiry_id, FacilityInquiry.facility_id == facility_id)
        .one_or_none()
    )
    if inquiry is None:
        raise LookupError("Inquiry not found")
    kind = str(payload.get("kind") or "").upper()
    if kind not in RESPONSE_KINDS:
        raise ValueError("יש לבחור סוג תשובה.")
    text = _text(payload.get("text"), "תשובה", required=kind in {"ALTERNATIVE", "NEED_INFO"})
    message = {
        "from": "FACILITY",
        "kind": kind,
        "text": text,
        "monthly_ils": _money(payload.get("monthly_ils"), "תשלום חודשי"),
        "deposit_ils": _money(payload.get("deposit_ils"), "פיקדון"),
        "at": _now(),
    }
    messages = json.loads(inquiry.messages_json)
    messages.append(message)
    inquiry.messages_json = json.dumps(messages, ensure_ascii=False)
    inquiry.status = kind
    db.add(
        FacilityAuditLog(
            facility_id=facility_id,
            user_id=user_id,
            field_name=f"inquiry:{inquiry.id}:respond",
            old_value=None,
            new_value=kind,
            user_role=(db.query(FacilityUser.role).filter(FacilityUser.id == user_id).scalar() or "UNKNOWN"),
        )
    )
    db.commit()
    from app.services.israel_notifications import notify

    notify(db, inquiry, "FAMILY", "FACILITY_REPLY")
    facility = db.query(Facility).filter(Facility.id == facility_id).one()
    return _view(inquiry, facility, for_facility=True)
