"""Family feedback on Israeli facilities (owner decision 2026-11-15: a trust layer).

Only a family that wrote to a facility through OOMNIK can rate it, using the private
link of that request, and only after saying it visited or moved in. The public page
shows averages only once MIN_TO_SHOW families have answered; free-text comments are
kept but not published (no moderation yet). Feedback never touches matching or ranking.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityFeedback
from app.services.israel_inquiries import _by_token, _text

MIN_TO_SHOW = 5
RELATIONS = {"VISITED": "ביקרנו במקום", "MOVED_IN": "בן המשפחה גר/ה שם"}
ASPECTS = [
    ("staff", "יחס הצוות"),
    ("care", "טיפול והשגחה"),
    ("cleanliness", "ניקיון ותחזוקה"),
    ("food", "אוכל"),
    ("family_contact", "קשר עם המשפחה"),
]


def feedback_form() -> Dict[str, Any]:
    return {
        "relations": [{"value": k, "label": v} for k, v in RELATIONS.items()],
        "aspects": [{"key": k, "label": v} for k, v in ASPECTS],
        "scale": [1, 2, 3, 4, 5],
        "min_to_show": MIN_TO_SHOW,
    }


def validate_feedback(payload: Dict[str, Any]) -> Dict[str, Any]:
    relation = str(payload.get("relation") or "").upper()
    if relation not in RELATIONS:
        raise ValueError("יש לבחור אם ביקרתם במקום או שבן המשפחה גר שם.")
    raw = payload.get("ratings") if isinstance(payload.get("ratings"), dict) else {}
    ratings: Dict[str, int] = {}
    for key, label in ASPECTS:
        value = raw.get(key)
        if value in (None, ""):
            continue  # "not relevant" is allowed; nothing is assumed
        try:
            number = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label}: ציון לא תקין.") from error
        if not 1 <= number <= 5:
            raise ValueError(f"{label}: הציון צריך להיות בין 1 ל-5.")
        ratings[key] = number
    if not ratings:
        raise ValueError("יש לדרג לפחות נושא אחד.")
    recommend = str(payload.get("recommend") or "").upper()
    if recommend not in {"YES", "NO"}:
        raise ValueError("יש לענות אם הייתם ממליצים על המקום.")
    return {"relation": relation, "ratings": ratings, "recommend": recommend, "comment": _text(payload.get("comment"), "הערה")}


def _own(row: Optional[FacilityFeedback]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {"relation": row.relation, "ratings": json.loads(row.ratings_json), "recommend": row.recommend, "comment": row.comment}


def family_feedback(db: Session, token: str) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    row = db.query(FacilityFeedback).filter(FacilityFeedback.inquiry_id == inquiry.id).one_or_none()
    return {"form": feedback_form(), "mine": _own(row)}


def submit_feedback(db: Session, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    inquiry = _by_token(db, token)
    data = validate_feedback(payload)
    row = db.query(FacilityFeedback).filter(FacilityFeedback.inquiry_id == inquiry.id).one_or_none()
    if row is None:
        row = FacilityFeedback(facility_id=inquiry.facility_id, inquiry_id=inquiry.id)
        db.add(row)
    row.relation = data["relation"]
    row.ratings_json = json.dumps(data["ratings"])
    row.recommend = data["recommend"]
    row.comment = data["comment"]
    db.commit()
    return {"form": feedback_form(), "mine": _own(row)}


def feedback_summary(db: Session, facility_id: Optional[int]) -> Dict[str, Any]:
    rows: List[FacilityFeedback] = (
        db.query(FacilityFeedback).filter(FacilityFeedback.facility_id == facility_id).all() if facility_id is not None else []
    )
    summary: Dict[str, Any] = {"count": len(rows), "min_to_show": MIN_TO_SHOW, "shown": len(rows) >= MIN_TO_SHOW}
    if not summary["shown"]:
        return summary
    aspects = []
    for key, label in ASPECTS:
        scores = [json.loads(r.ratings_json).get(key) for r in rows]
        scores = [s for s in scores if s is not None]
        aspects.append({"key": key, "label": label, "average": round(sum(scores) / len(scores), 1) if scores else None, "answers": len(scores)})
    summary["aspects"] = aspects
    summary["recommend_pct"] = round(100 * sum(r.recommend == "YES" for r in rows) / len(rows))
    summary["moved_in"] = sum(r.relation == "MOVED_IN" for r in rows)
    return summary


def facility_summary_by_canonical_id(db: Session, canonical_id: str) -> Dict[str, Any]:
    facility = db.query(Facility).filter(Facility.cms_id == canonical_id).one_or_none()
    return feedback_summary(db, facility.id if facility else None)
