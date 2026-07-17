import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set

from sqlalchemy.orm import Session

from app.models.facility import FacilityActivityCategory

ALLOWED_ACTIVITY_CATEGORIES = [
    "movies",
    "music",
    "lectures",
    "exercise",
    "gardening",
    "religious",
    "social",
]

_ACTIVITY_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "movies": [re.compile(r"\bmovie\b|\bmovies\b|\bcinema\b|\bfilm\b", re.IGNORECASE)],
    "music": [re.compile(r"\bmusic\b|\bconcert\b|\bchoir\b|\bsinging\b", re.IGNORECASE)],
    "lectures": [re.compile(r"\blecture\b|\btalk\b|\bseminar\b|\bclass\b", re.IGNORECASE)],
    "exercise": [re.compile(r"\bexercise\b|\bfitness\b|\byoga\b|\bstretch\b|\bworkout\b", re.IGNORECASE)],
    "gardening": [re.compile(r"\bgarden\b|\bgardening\b|\bhorticulture\b", re.IGNORECASE)],
    "religious": [re.compile(r"\breligious\b|\bservice\b|\bprayer\b|\bchapel\b|\bworship\b", re.IGNORECASE)],
    "social": [re.compile(r"\bsocial\b|\bcommunity\b|\bmeetup\b|\bgroup\b|\bgame\b", re.IGNORECASE)],
}


def _normalize_text_items(source_type: str, content: str) -> List[str]:
    normalized_type = source_type.strip().lower()

    if normalized_type == "google_calendar":
        return _extract_from_google_calendar(content)
    if normalized_type == "ics":
        return _extract_from_ics(content)
    if normalized_type == "csv":
        return _extract_from_csv(content)
    if normalized_type == "pdf":
        return _extract_from_pdf(content)

    raise ValueError(f"Unsupported source_type: {source_type}")


def _extract_from_google_calendar(content: str) -> List[str]:
    text_items: List[str] = []
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return text_items

    events: Iterable[dict] = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
    for event in events:
        if not isinstance(event, dict):
            continue
        summary = str(event.get("summary") or "").strip()
        description = str(event.get("description") or "").strip()
        combined = " ".join(part for part in [summary, description] if part)
        if combined:
            text_items.append(combined)

    return text_items


def _extract_from_ics(content: str) -> List[str]:
    summaries = re.findall(r"^SUMMARY:(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
    descriptions = re.findall(r"^DESCRIPTION:(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
    return [item.strip() for item in summaries + descriptions if item.strip()]


def _extract_from_csv(content: str) -> List[str]:
    text_items: List[str] = []
    stream = io.StringIO(content)
    reader = csv.DictReader(stream)
    for row in reader:
        combined = " ".join(
            str(row.get(key) or "")
            for key in ["title", "event", "name", "summary", "description", "category"]
        ).strip()
        if combined:
            text_items.append(combined)
    return text_items


def _extract_from_pdf(content: str) -> List[str]:
    # V1: accept extracted text payload from uploader and parse line-level signals.
    # This avoids storing schedule/timestamps and only classifies public categories.
    return [line.strip() for line in content.splitlines() if line.strip()]


def classify_activity_categories(source_type: str, content: str) -> Dict[str, int]:
    text_items = _normalize_text_items(source_type=source_type, content=content)
    counts = {category: 0 for category in ALLOWED_ACTIVITY_CATEGORIES}

    for item in text_items:
        for category, patterns in _ACTIVITY_PATTERNS.items():
            if any(pattern.search(item) for pattern in patterns):
                counts[category] += 1

    return counts


def import_activity_categories(
    db: Session,
    facility_id: int,
    source_type: str,
    content: str,
    updated_by_user_id: int | None = None,
) -> Dict[str, object]:
    if source_type.strip().lower() not in {"google_calendar", "ics", "csv", "pdf"}:
        raise ValueError("source_type must be one of: google_calendar, ics, csv, pdf")

    counts = classify_activity_categories(source_type=source_type, content=content)
    now = datetime.now(timezone.utc)

    existing = {
        row.category: row
        for row in db.query(FacilityActivityCategory).filter(FacilityActivityCategory.facility_id == facility_id).all()
    }

    for category in ALLOWED_ACTIVITY_CATEGORIES:
        count = counts.get(category, 0)
        availability = "YES" if count > 0 else "UNKNOWN"
        confidence = 85.0 if count >= 3 else 70.0 if count > 0 else 40.0

        row = existing.get(category)
        if row is None:
            row = FacilityActivityCategory(
                facility_id=facility_id,
                category=category,
                availability=availability,
                confidence=confidence,
                import_source=source_type.lower(),
                last_imported_at=now,
                updated_by_user_id=updated_by_user_id,
            )
            db.add(row)
        else:
            row.availability = availability
            row.confidence = confidence
            row.import_source = source_type.lower()
            row.last_imported_at = now
            row.updated_by_user_id = updated_by_user_id

    db.commit()

    public_categories = [
        {
            "category": category,
            "availability": "YES" if counts.get(category, 0) > 0 else "UNKNOWN",
            "confidence": 85.0 if counts.get(category, 0) >= 3 else 70.0 if counts.get(category, 0) > 0 else 40.0,
        }
        for category in ALLOWED_ACTIVITY_CATEGORIES
    ]

    return {
        "facility_id": facility_id,
        "source_type": source_type.lower(),
        "imported_at": now.isoformat(),
        "categories": public_categories,
        "privacy_policy": "Exact schedules are never exposed publicly; only category-level availability is returned.",
    }


def get_public_activity_categories(db: Session, facility_id: int) -> List[Dict[str, object]]:
    rows = db.query(FacilityActivityCategory).filter(FacilityActivityCategory.facility_id == facility_id).all()

    by_category = {row.category: row for row in rows}
    result: List[Dict[str, object]] = []
    for category in ALLOWED_ACTIVITY_CATEGORIES:
        row = by_category.get(category)
        result.append(
            {
                "category": category,
                "availability": row.availability if row else "UNKNOWN",
                "confidence": float(row.confidence) if row and row.confidence is not None else 0.0,
            }
        )

    return result
