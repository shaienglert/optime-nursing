"""Visit coordination for Israeli families (owner flow 2026-11-17).

Lives inside an inquiry: the family proposes dates through its private link, the
facility answers from its portal session. Dates are local Israeli dates; the exact
time is set only by the facility. Nothing here touches matching or ranking.

States:
  REQUESTED          family proposed 1-3 dates, waiting for the facility
  FACILITY_PROPOSED  facility proposed another date/time, waiting for the family
  CONFIRMED          one date and time agreed
  CANCELLED          cancelled by either side (the family may propose again)
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityAuditLog, FacilityInquiry, FacilityUser, FacilityVisit
from app.services.israel_inquiries import _by_token, _text

TZ = ZoneInfo("Asia/Jerusalem")
PARTS = {"MORNING": "בוקר (8:00-12:00)", "NOON": "צהריים (12:00-15:00)", "AFTERNOON": "אחר הצהריים (15:00-19:00)"}
MODES = {"IN_PERSON": "ביקור במקום", "VIDEO": "שיחת וידאו"}
STATUS_HE = {
    "REQUESTED": "ממתין לאישור המוסד",
    "FACILITY_PROPOSED": "המוסד הציע מועד אחר, ממתין לאישורכם",
    "CONFIRMED": "הביקור נקבע",
    "CANCELLED": "הביקור בוטל",
}
MAX_SLOTS = 3
HORIZON_DAYS = 60
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _today() -> date:
    return datetime.now(TZ).date()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _date(value: Any) -> date:
    try:
        day = date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("תאריך לא תקין.") from error
    if day <= _today():
        raise ValueError("אפשר לבחור תאריך החל ממחר.")
    if day > _today() + timedelta(days=HORIZON_DAYS):
        raise ValueError(f"אפשר לבחור תאריך בתוך {HORIZON_DAYS} יום.")
    return day


def _time(value: Any) -> str:
    text = str(value or "").strip()
    if not _TIME_RE.match(text):
        raise ValueError("שעה לא תקינה (למשל 10:30).")
    return text


def validate_family_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = payload.get("slots") if isinstance(payload.get("slots"), list) else []
    slots, seen = [], set()
    for item in raw[:MAX_SLOTS]:
        if not isinstance(item, dict):
            continue
        day = _date(item.get("date"))
        part = str(item.get("part") or "").upper()
        if part not in PARTS:
            raise ValueError("יש לבחור חלק ביום.")
        if (day, part) in seen:
            continue
        seen.add((day, part))
        slots.append({"date": day.isoformat(), "part": part})
    if not slots:
        raise ValueError("יש לבחור לפחות מועד אחד.")
    if len(raw) > MAX_SLOTS:
        raise ValueError(f"אפשר להציע עד {MAX_SLOTS} מועדים.")
    mode = str(payload.get("mode") or "IN_PERSON").upper()
    if mode not in MODES:
        raise ValueError("סוג ביקור לא תקין.")
    try:
        visitors = int(payload.get("visitors") or 1)
    except (TypeError, ValueError) as error:
        raise ValueError("מספר מבקרים לא תקין.") from error
    if not 1 <= visitors <= 8:
        raise ValueError("מספר המבקרים צריך להיות בין 1 ל-8.")
    return {"slots": slots, "mode": mode, "visitors": visitors, "note": _text(payload.get("note"), "הערה")}


def _he_date(value: str) -> str:
    day = date.fromisoformat(value)
    names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    return f"יום {names[day.weekday()]}, {day.day}.{day.month}.{day.year}"


def visit_view(visit: Optional[FacilityVisit]) -> Optional[Dict[str, Any]]:
    if visit is None:
        return None
    request = json.loads(visit.request_json)
    confirmed = json.loads(visit.confirmed_json) if visit.confirmed_json else None
    view = {
        "status": visit.status,
        "status_label": STATUS_HE[visit.status],
        "mode": request["mode"],
        "mode_label": MODES[request["mode"]],
        "visitors": request["visitors"],
        "note": request.get("note"),
        "slots": [{**s, "label": f"{_he_date(s['date'])}, {PARTS[s['part']]}"} for s in request["slots"]],
        "confirmed": None,
        "history": json.loads(visit.history_json or "[]"),
    }
    if confirmed:
        view["confirmed"] = {**confirmed, "label": f"{_he_date(confirmed['date'])}, בשעה {confirmed['time']}"}
    return view


def _visit_for(db: Session, inquiry: FacilityInquiry) -> Optional[FacilityVisit]:
    return db.query(FacilityVisit).filter(FacilityVisit.inquiry_id == inquiry.id).one_or_none()


def _log(visit: FacilityVisit, actor: str, action: str, **extra: Any) -> None:
    history = json.loads(visit.history_json or "[]")
    history.append({"by": actor, "action": action, "at": _now(), **{k: v for k, v in extra.items() if v is not None}})
    visit.history_json = json.dumps(history, ensure_ascii=False)


# ---- family side (private inquiry link) -------------------------------------

def family_visit(db: Session, token: str) -> Optional[Dict[str, Any]]:
    return visit_view(_visit_for(db, _by_token(db, token)))


def family_request_visit(db: Session, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    data = validate_family_request(payload)
    visit = _visit_for(db, inquiry)
    if visit is not None and visit.status == "CONFIRMED":
        raise ValueError("כבר נקבע ביקור. כדי לשנות, בטלו אותו קודם.")
    if visit is None:
        visit = FacilityVisit(inquiry_id=inquiry.id, facility_id=inquiry.facility_id, history_json="[]")
        db.add(visit)
    visit.status = "REQUESTED"
    visit.request_json = json.dumps(data, ensure_ascii=False)
    visit.confirmed_json = None
    _log(visit, "FAMILY", "REQUESTED")
    db.commit()
    return visit_view(visit)


def family_answer_visit(db: Session, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    visit = _visit_for(db, inquiry)
    if visit is None:
        raise LookupError("Visit not found")
    action = str(payload.get("action") or "").upper()
    if action == "ACCEPT":
        if visit.status != "FACILITY_PROPOSED":
            raise ValueError("אין הצעה של המוסד שממתינה לאישור.")
        proposal = json.loads(visit.confirmed_json)
        if date.fromisoformat(proposal["date"]) <= _today():
            raise ValueError("המועד שהוצע כבר עבר. אפשר להציע מועדים חדשים.")
        visit.status = "CONFIRMED"
        _log(visit, "FAMILY", "ACCEPTED")
    elif action == "CANCEL":
        if visit.status == "CANCELLED":
            raise ValueError("הביקור כבר בוטל.")
        visit.status = "CANCELLED"
        _log(visit, "FAMILY", "CANCELLED", note=_text(payload.get("note"), "הערה"))
    else:
        raise ValueError("פעולה לא תקינה.")
    db.commit()
    return visit_view(visit)


# ---- facility side (portal session) -----------------------------------------

def facility_answer_visit(db: Session, facility_id: int, user_id: int, inquiry_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    inquiry = (
        db.query(FacilityInquiry)
        .filter(FacilityInquiry.id == inquiry_id, FacilityInquiry.facility_id == facility_id)
        .one_or_none()
    )
    if inquiry is None:
        raise LookupError("Inquiry not found")
    visit = _visit_for(db, inquiry)
    if visit is None:
        raise LookupError("Visit not found")
    action = str(payload.get("action") or "").upper()
    note = _text(payload.get("note"), "הערה")
    if action == "CONFIRM":
        if visit.status != "REQUESTED":
            raise ValueError("אין בקשת ביקור שממתינה לאישור.")
        slots = json.loads(visit.request_json)["slots"]
        try:
            slot = slots[int(payload.get("slot_index"))]
        except (TypeError, ValueError, IndexError) as error:
            raise ValueError("יש לבחור אחד מהמועדים שהמשפחה הציעה.") from error
        _date(slot["date"])  # still in the future
        visit.confirmed_json = json.dumps({"date": slot["date"], "time": _time(payload.get("time")), "note": note}, ensure_ascii=False)
        visit.status = "CONFIRMED"
    elif action == "PROPOSE":
        if visit.status not in {"REQUESTED", "FACILITY_PROPOSED", "CONFIRMED"}:
            raise ValueError("אי אפשר להציע מועד לביקור שבוטל.")
        visit.confirmed_json = json.dumps(
            {"date": _date(payload.get("date")).isoformat(), "time": _time(payload.get("time")), "note": note}, ensure_ascii=False
        )
        visit.status = "FACILITY_PROPOSED"
    elif action == "CANCEL":
        if visit.status == "CANCELLED":
            raise ValueError("הביקור כבר בוטל.")
        visit.status = "CANCELLED"
    else:
        raise ValueError("פעולה לא תקינה.")
    _log(visit, "FACILITY", action, note=note)
    db.add(
        FacilityAuditLog(
            facility_id=facility_id,
            user_id=user_id,
            field_name=f"inquiry:{inquiry.id}:visit",
            old_value=None,
            new_value=action,
            user_role=(db.query(FacilityUser.role).filter(FacilityUser.id == user_id).scalar() or "UNKNOWN"),
        )
    )
    db.commit()
    return visit_view(visit)


def facility_visits(db: Session, facility_id: int) -> Dict[int, Dict[str, Any]]:
    rows = db.query(FacilityVisit).filter(FacilityVisit.facility_id == facility_id).all()
    return {row.inquiry_id: visit_view(row) for row in rows}


def visit_ics(db: Session, token: str) -> str:
    """Calendar file for a confirmed visit (Israel local time)."""
    inquiry = _by_token(db, token)
    visit = _visit_for(db, inquiry)
    if visit is None or visit.status != "CONFIRMED":
        raise LookupError("No confirmed visit")
    facility = db.query(Facility).filter(Facility.id == inquiry.facility_id).one()
    confirmed = json.loads(visit.confirmed_json)
    start = datetime.fromisoformat(f"{confirmed['date']}T{confirmed['time']}:00").replace(tzinfo=TZ)
    end = start + timedelta(hours=1)
    fmt = "%Y%m%dT%H%M%SZ"
    mode = MODES[json.loads(visit.request_json)["mode"]]
    location = ", ".join(x for x in [facility.address, facility.city] if x and x != "x")

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//OOMNIK//Visit//HE", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
        f"UID:oomnik-visit-{visit.id}@oomnik.co.il",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime(fmt)}",
        f"DTSTART:{start.astimezone(timezone.utc).strftime(fmt)}",
        f"DTEND:{end.astimezone(timezone.utc).strftime(fmt)}",
        f"SUMMARY:{esc(mode + ': ' + (facility.name or ''))}",
        f"LOCATION:{esc(location)}" if location and mode != MODES["VIDEO"] else "",
        f"DESCRIPTION:{esc(confirmed.get('note') or 'נקבע דרך OOMNIK')}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(line for line in lines if line) + "\r\n"


# ---- published visiting hours (facility calendar) -----------------------------

from app.models.facility import FacilityVisitSchedule  # noqa: E402

DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]  # Israeli week order
DAYS_HE = {"SUN": "ראשון", "MON": "שני", "TUE": "שלישי", "WED": "רביעי", "THU": "חמישי", "FRI": "שישי", "SAT": "שבת"}
_PY_WEEKDAY = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
SLOT_MINUTES = (30, 45, 60, 90)
BOOKING_WINDOW_DAYS = 30


def _minutes(value: str) -> int:
    hours, minutes = _time(value).split(":")
    return int(hours) * 60 + int(minutes)


def validate_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    weekly_in = payload.get("weekly") if isinstance(payload.get("weekly"), dict) else {}
    weekly: Dict[str, List[List[str]]] = {}
    for day in DAYS:
        ranges = []
        for item in (weekly_in.get(day) or [])[:3]:
            start, end = _time(item[0]), _time(item[1])
            if _minutes(end) <= _minutes(start):
                raise ValueError(f"יום {DAYS_HE[day]}: שעת הסיום צריכה להיות אחרי שעת ההתחלה.")
            ranges.append([start, end])
        ranges.sort()
        for (s1, e1), (s2, _) in zip(ranges, ranges[1:]):
            if _minutes(s2) < _minutes(e1):
                raise ValueError(f"יום {DAYS_HE[day]}: טווחי השעות חופפים.")
        if ranges:
            weekly[day] = ranges
    try:
        slot = int(payload.get("slot_minutes") or 45)
        capacity = int(payload.get("capacity") or 1)
        lead = int(payload.get("lead_hours") or 24)
    except (TypeError, ValueError) as error:
        raise ValueError("ערך מספרי לא תקין.") from error
    if slot not in SLOT_MINUTES:
        raise ValueError("משך ביקור לא תקין.")
    if not 1 <= capacity <= 10:
        raise ValueError("מספר המשפחות בכל מועד צריך להיות בין 1 ל-10.")
    if not 0 <= lead <= 168:
        raise ValueError("זמן ההתראה המינימלי צריך להיות בין 0 ל-168 שעות.")
    blocked = sorted({date.fromisoformat(str(d)).isoformat() for d in payload.get("blocked_dates") or []})
    modes = [m for m in (payload.get("modes") or ["IN_PERSON"]) if m in MODES] or ["IN_PERSON"]
    return {"weekly": weekly, "slot_minutes": slot, "capacity": capacity, "lead_hours": lead, "blocked_dates": blocked, "modes": modes}


def load_schedule(db: Session, facility_id: int) -> Optional[Dict[str, Any]]:
    row = db.query(FacilityVisitSchedule).filter(FacilityVisitSchedule.facility_id == facility_id).one_or_none()
    return json.loads(row.schedule_json) if row else None


def save_schedule(db: Session, facility_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = validate_schedule(payload)
    row = db.query(FacilityVisitSchedule).filter(FacilityVisitSchedule.facility_id == facility_id).one_or_none()
    if row is None:
        row = FacilityVisitSchedule(facility_id=facility_id)
        db.add(row)
    row.schedule_json = json.dumps(data, ensure_ascii=False)
    db.add(
        FacilityAuditLog(
            facility_id=facility_id, user_id=user_id, field_name="visit_schedule", old_value=None, new_value="SAVED",
            user_role=(db.query(FacilityUser.role).filter(FacilityUser.id == user_id).scalar() or "UNKNOWN"),
        )
    )
    db.commit()
    return data


def _booked(db: Session, facility_id: int) -> Dict[Tuple[str, str], int]:
    counts: Dict[Tuple[str, str], int] = {}
    for row in db.query(FacilityVisit).filter(FacilityVisit.facility_id == facility_id, FacilityVisit.status == "CONFIRMED"):
        confirmed = json.loads(row.confirmed_json or "{}")
        key = (confirmed.get("date"), confirmed.get("time"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def open_slots(db: Session, facility_id: int, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    """The facility's calendar for the next BOOKING_WINDOW_DAYS days: every slot within its
    published hours, minus closed dates, past/too-soon times and full slots."""
    schedule = load_schedule(db, facility_id)
    if not schedule or not schedule.get("weekly"):
        return {"configured": False, "days": []}
    now = (now or datetime.now(TZ)).astimezone(TZ)
    earliest = now + timedelta(hours=int(schedule["lead_hours"]))
    booked = _booked(db, facility_id)
    by_weekday = {_PY_WEEKDAY[d]: ranges for d, ranges in schedule["weekly"].items()}
    blocked = set(schedule.get("blocked_dates") or [])
    days = []
    for offset in range(BOOKING_WINDOW_DAYS + 1):
        day = now.date() + timedelta(days=offset)
        iso = day.isoformat()
        slots = []
        if iso not in blocked:
            for start, end in by_weekday.get(day.weekday(), []):
                minute = _minutes(start)
                while minute + schedule["slot_minutes"] <= _minutes(end):
                    hhmm = f"{minute // 60:02d}:{minute % 60:02d}"
                    at = datetime.fromisoformat(f"{iso}T{hhmm}:00").replace(tzinfo=TZ)
                    left = schedule["capacity"] - booked.get((iso, hhmm), 0)
                    if at >= earliest and left > 0:
                        slots.append({"time": hhmm, "left": left})
                    minute += schedule["slot_minutes"]
        days.append({"date": iso, "label": _he_date(iso), "slots": slots})
    return {
        "configured": True,
        "slot_minutes": schedule["slot_minutes"],
        "modes": [{"value": m, "label": MODES[m]} for m in schedule.get("modes") or ["IN_PERSON"]],
        "days": days,
    }


def family_slots(db: Session, token: str) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    return open_slots(db, inquiry.facility_id)


def family_book_visit(db: Session, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Book one open slot from the facility's calendar; confirmed at once."""
    inquiry = _by_token(db, token)
    visit = _visit_for(db, inquiry)
    if visit is not None and visit.status == "CONFIRMED":
        raise ValueError("כבר נקבע ביקור. כדי לשנות, בטלו אותו קודם.")
    day, hhmm = str(payload.get("date") or ""), str(payload.get("time") or "")
    calendar = open_slots(db, inquiry.facility_id)
    if not calendar["configured"]:
        raise ValueError("המוסד עוד לא פרסם שעות ביקור. אפשר להציע מועדים.")
    if not any(d["date"] == day and any(s["time"] == hhmm for s in d["slots"]) for d in calendar["days"]):
        raise ValueError("המועד הזה כבר לא פנוי. בחרו מועד אחר.")
    mode = str(payload.get("mode") or "IN_PERSON").upper()
    if mode not in {m["value"] for m in calendar["modes"]}:
        raise ValueError("סוג ביקור לא זמין במוסד הזה.")
    try:
        visitors = int(payload.get("visitors") or 1)
    except (TypeError, ValueError) as error:
        raise ValueError("מספר מבקרים לא תקין.") from error
    if not 1 <= visitors <= 8:
        raise ValueError("מספר המבקרים צריך להיות בין 1 ל-8.")
    request = {"slots": [], "mode": mode, "visitors": visitors, "note": _text(payload.get("note"), "הערה"), "booked_from_calendar": True}
    if visit is None:
        visit = FacilityVisit(inquiry_id=inquiry.id, facility_id=inquiry.facility_id, history_json="[]")
        db.add(visit)
    visit.status = "CONFIRMED"
    visit.request_json = json.dumps(request, ensure_ascii=False)
    visit.confirmed_json = json.dumps({"date": day, "time": hhmm, "note": None}, ensure_ascii=False)
    _log(visit, "FAMILY", "BOOKED")
    db.commit()
    return visit_view(visit)


def synthetic_schedule(canonical_id: str, religious: Optional[str]) -> Dict[str, Any]:
    """Deterministic visiting hours for synthetic test facilities only."""
    n = int(re.sub(r"\D", "", canonical_id) or 0)
    observant = str(religious or "").upper() in {"RELIGIOUS", "HAREDI"}
    morning, afternoon = ["10:00", "12:00"], ["16:00", "18:30"]
    weekly = {d: [morning, afternoon] if n % 2 else [afternoon] for d in ["SUN", "MON", "TUE", "WED", "THU"]}
    weekly["FRI"] = [["09:30", "12:00"]]
    if not observant and n % 3 == 0:
        weekly["SAT"] = [["11:00", "13:00"]]
    return validate_schedule({"weekly": weekly, "slot_minutes": [30, 45, 60][n % 3], "capacity": 1 + n % 2, "lead_hours": 24,
                              "modes": ["IN_PERSON", "VIDEO"] if n % 4 else ["IN_PERSON"]})
