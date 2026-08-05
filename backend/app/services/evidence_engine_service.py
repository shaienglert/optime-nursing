from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.evidence_engine import FacilityEvidenceRegistry, FacilityEvidenceRegistryVersion
from app.models.facility import (
    Facility,
    FacilityIntelligenceProfile,
    FacilityReview,
    FacilityVerificationResponse,
    Inspection,
    ResidentOutcome,
)
from app.services.facility_parameter_service import get_canonical_facility_index, get_runtime_metadata

REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"
EVIDENCE_PATH = DATABASE_DIR / "florida_facility_parameter_evidence.json"
REGISTRY_PATH = DATABASE_DIR / "optime_parameter_registry.json"

SOURCE_RELIABILITY = {
    "CMS": 0.98,
    "CMS_NURSING_HOME_COMPARE": 0.97,
    "STATE_INSPECTIONS": 0.95,
    "FACILITY_PORTAL": 0.86,
    "EXTERNAL_DISCOVERY": 0.72,
    "HUMAN_INTELLIGENCE": 0.74,
    "RESIDENT_OUTCOMES": 0.89,
    "MANUAL_RESEARCH": 0.8,
    "UNKNOWN": 0.5,
}

VERIFIED_STATUSES = {"VERIFIED", "PARTIALLY_VERIFIED"}


@dataclass
class NormalizedEvidenceItem:
    evidence_id: str
    facility_id: Optional[int]
    parameter_id: str
    parameter_name: str
    parameter_value: Optional[str]
    source: str
    source_type: str
    source_url: str
    collection_method: str
    collected_at: datetime
    verified_at: Optional[datetime]
    verification_status: str
    confidence_score: float
    importance_score: float
    expires_at: Optional[datetime]
    runtime_version: str
    connector: str
    affects_recommendation: bool
    dedup_group_key: str
    raw_payload: Dict[str, Any]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ["%Y-%m-%d", "%m/%d/%Y"]:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _stable_hash(*parts: Any) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _normalize_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _derive_source_type_from_row(row: Dict[str, Any]) -> str:
    source = str(row.get("source") or "")
    provenance = row.get("provenance") or {}
    family = str(provenance.get("source_family") or "").upper()

    if family == "CMS" or source.startswith("CMS"):
        if "Provider Information" in source or "Nursing Home" in source:
            return "CMS_NURSING_HOME_COMPARE"
        if "Inspection" in source or "Deficiencies" in source:
            return "STATE_INSPECTIONS"
        return "CMS"
    if family == "RUNTIME_DISCOVERY":
        return "EXTERNAL_DISCOVERY"
    if family == "NPPES":
        return "CMS"
    return "UNKNOWN"


def _status_from_value(raw_value: Any, source: str) -> str:
    text = str(raw_value or "").strip().upper()
    if not text or text in {"UNKNOWN", "NOT VERIFIED"}:
        return "UNKNOWN"
    if source.strip().lower() == "not verified":
        return "UNKNOWN"
    return "VERIFIED"


def _base_confidence(source_type: str, status: str) -> float:
    source_weight = SOURCE_RELIABILITY.get(source_type, SOURCE_RELIABILITY["UNKNOWN"])
    status_bonus = 0.0
    if status == "VERIFIED":
        status_bonus = 0.08
    elif status == "PARTIALLY_VERIFIED":
        status_bonus = 0.03
    return max(0.0, min(1.0, source_weight + status_bonus))


def _importance_score(parameter_id: str, registry_index: Dict[str, Dict[str, Any]]) -> float:
    parameter = registry_index.get(parameter_id) or {}
    score = 40.0
    if parameter.get("hard_filter_eligibility"):
        score += 35.0
    if parameter.get("ranking_eligibility"):
        score += 20.0
    family = str(parameter.get("family") or "")
    if family in {"CARE_NURSING", "REHABILITATION", "SPECIALIZED_CARE"}:
        score += 5.0
    return min(100.0, score)


def _expires_at(verified_at: Optional[datetime], source_type: str, parameter_id: str) -> Optional[datetime]:
    base = verified_at or _now()
    key = parameter_id.lower()
    if any(token in key for token in ["price", "rate", "availability", "beds"]):
        return base + timedelta(days=30)
    if source_type in {"STATE_INSPECTIONS", "CMS", "CMS_NURSING_HOME_COMPARE"}:
        return base + timedelta(days=180)
    if source_type == "FACILITY_PORTAL":
        return base + timedelta(days=120)
    return base + timedelta(days=90)


def _parse_signal_details(raw: Optional[str]) -> List[Dict[str, Any]]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    except json.JSONDecodeError:
        return []
    return []


def _facility_id_map(db: Session) -> Dict[str, int]:
    return {str(row.cms_id): int(row.id) for row in db.query(Facility.id, Facility.cms_id).all() if row.cms_id}


def _canonical_to_facility_id(db: Session) -> Dict[str, int]:
    ccn_to_facility_id = _facility_id_map(db)
    canonical_index = get_canonical_facility_index()
    mapping: Dict[str, int] = {}
    for canonical_id, row in canonical_index.items():
        source_identity_ids = row.get("source_identity_ids") or {}
        cms_ccn = str(source_identity_ids.get("cms_ccn") or "").strip()
        if cms_ccn and cms_ccn in ccn_to_facility_id:
            mapping[canonical_id] = ccn_to_facility_id[cms_ccn]
    return mapping


def _parameter_registry_index() -> Dict[str, Dict[str, Any]]:
    payload = _read_json(REGISTRY_PATH)
    rows = payload.get("records") or []
    return {str(row.get("parameter_id")): row for row in rows if row.get("parameter_id")}


def _normalize_from_parameter_runtime(db: Session, runtime_version: str, registry_index: Dict[str, Dict[str, Any]]) -> List[NormalizedEvidenceItem]:
    payload = _read_json(EVIDENCE_PATH)
    rows = payload.get("records") or []
    canonical_map = _canonical_to_facility_id(db)
    items: List[NormalizedEvidenceItem] = []

    for row in rows:
        canonical_id = str(row.get("canonical_facility_id") or "").strip()
        facility_id = canonical_map.get(canonical_id)
        parameter_id = str(row.get("parameter_id") or "").strip()
        if not parameter_id:
            continue
        parameter_name = str((registry_index.get(parameter_id) or {}).get("display_name") or parameter_id)
        source = str(row.get("source") or "Unknown")
        source_type = _derive_source_type_from_row(row)
        source_url = str((row.get("provenance") or {}).get("source_url") or "")
        collected_at = _parse_datetime(row.get("evidence_date") or row.get("last_verified")) or _now()
        verified_at = _parse_datetime(row.get("last_verified")) or collected_at
        parameter_value = _normalize_value(row.get("value") if row.get("value") is not None else row.get("evidence_value"))
        verification_status = _status_from_value(parameter_value, source)
        confidence = _base_confidence(source_type, verification_status)
        importance = _importance_score(parameter_id, registry_index)
        dedup_key = _stable_hash(facility_id, parameter_id, parameter_value, source_type, source_url)
        evidence_id = f"evr-{_stable_hash('runtime', canonical_id, parameter_id, source, row.get('source_record_id'), row.get('evidence_date'))[:20]}"

        items.append(
            NormalizedEvidenceItem(
                evidence_id=evidence_id,
                facility_id=facility_id,
                parameter_id=parameter_id,
                parameter_name=parameter_name,
                parameter_value=parameter_value,
                source=source,
                source_type=source_type,
                source_url=source_url,
                collection_method="runtime_parameter_artifact",
                collected_at=collected_at,
                verified_at=verified_at,
                verification_status=verification_status,
                confidence_score=confidence,
                importance_score=importance,
                expires_at=_expires_at(verified_at, source_type, parameter_id),
                runtime_version=runtime_version,
                connector="RUNTIME_PARAMETER_EVIDENCE",
                affects_recommendation=bool((registry_index.get(parameter_id) or {}).get("ranking_eligibility") or (registry_index.get(parameter_id) or {}).get("hard_filter_eligibility")),
                dedup_group_key=dedup_key,
                raw_payload=row,
            )
        )

    return items


def _normalize_from_facility_portal(db: Session, runtime_version: str, registry_index: Dict[str, Dict[str, Any]]) -> List[NormalizedEvidenceItem]:
    rows = db.query(FacilityVerificationResponse).all()
    items: List[NormalizedEvidenceItem] = []

    for row in rows:
        parameter_id = str(row.capability or "").strip()
        if not parameter_id:
            continue
        parameter_name = str((registry_index.get(parameter_id) or {}).get("display_name") or parameter_id)
        source = str(row.source or "FACILITY_PORTAL")
        source_type = "FACILITY_PORTAL"
        value = row.value.value if hasattr(row.value, "value") else str(row.value)
        verification_status = "UNKNOWN" if str(value).upper() == "UNKNOWN" else "VERIFIED"
        collected_at = row.created_at or _now()
        verified_at = row.verified_at
        dedup_key = _stable_hash(row.facility_id, parameter_id, value, source_type)
        evidence_id = f"evp-{_stable_hash('portal', row.facility_id, parameter_id, row.id)[:20]}"

        items.append(
            NormalizedEvidenceItem(
                evidence_id=evidence_id,
                facility_id=row.facility_id,
                parameter_id=parameter_id,
                parameter_name=parameter_name,
                parameter_value=_normalize_value(value),
                source=source,
                source_type=source_type,
                source_url="",
                collection_method="provider_portal_response",
                collected_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                verified_at=verified_at if verified_at and verified_at.tzinfo else (verified_at.replace(tzinfo=timezone.utc) if verified_at else None),
                verification_status=verification_status,
                confidence_score=_base_confidence(source_type, verification_status),
                importance_score=_importance_score(parameter_id, registry_index),
                expires_at=row.expires_at if row.expires_at and row.expires_at.tzinfo else (row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at else None),
                runtime_version=runtime_version,
                connector="FACILITY_PORTAL",
                affects_recommendation=bool((registry_index.get(parameter_id) or {}).get("ranking_eligibility") or (registry_index.get(parameter_id) or {}).get("hard_filter_eligibility")),
                dedup_group_key=dedup_key,
                raw_payload={
                    "request_id": row.request_id,
                    "response_id": row.id,
                    "notes": row.notes,
                },
            )
        )

    return items


def _normalize_from_inspections(db: Session, runtime_version: str, registry_index: Dict[str, Dict[str, Any]]) -> List[NormalizedEvidenceItem]:
    rows = db.query(Inspection).all()
    mapping = {
        "deficiency_count": "deficiency_count",
        "severe_deficiency_count": "deficiency_severity",
        "payment_denials_count": "payment_denials",
        "fine_amount": "penalties_fines",
    }
    items: List[NormalizedEvidenceItem] = []

    for row in rows:
        collected_at = _parse_datetime(row.inspection_date) or row.created_at or _now()
        verified_at = collected_at
        for field_name, parameter_id in mapping.items():
            value = getattr(row, field_name)
            if value is None:
                continue
            parameter_name = str((registry_index.get(parameter_id) or {}).get("display_name") or parameter_id)
            value_text = _normalize_value(value)
            verification_status = _status_from_value(value_text, row.source_name or "")
            source = row.source_name or "State inspections"
            source_type = "STATE_INSPECTIONS"
            dedup_key = _stable_hash(row.facility_id, parameter_id, value_text, source_type, row.inspection_date)
            evidence_id = f"evi-{_stable_hash('inspection', row.id, parameter_id)[:20]}"

            items.append(
                NormalizedEvidenceItem(
                    evidence_id=evidence_id,
                    facility_id=row.facility_id,
                    parameter_id=parameter_id,
                    parameter_name=parameter_name,
                    parameter_value=value_text,
                    source=source,
                    source_type=source_type,
                    source_url="https://data.cms.gov/provider-data/",
                    collection_method="inspection_ingestion",
                    collected_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                    verified_at=verified_at if verified_at.tzinfo else verified_at.replace(tzinfo=timezone.utc),
                    verification_status=verification_status,
                    confidence_score=_base_confidence(source_type, verification_status),
                    importance_score=_importance_score(parameter_id, registry_index),
                    expires_at=_expires_at(verified_at, source_type, parameter_id),
                    runtime_version=runtime_version,
                    connector="STATE_INSPECTIONS",
                    affects_recommendation=True,
                    dedup_group_key=dedup_key,
                    raw_payload={"inspection_id": row.id},
                )
            )

    return items


def _normalize_from_human_and_outcomes(db: Session, runtime_version: str, registry_index: Dict[str, Dict[str, Any]]) -> List[NormalizedEvidenceItem]:
    items: List[NormalizedEvidenceItem] = []

    profiles = db.query(FacilityIntelligenceProfile).all()
    for profile in profiles:
        signal_details = _parse_signal_details(profile.signal_details)
        for index, detail in enumerate(signal_details):
            parameter_id = str(detail.get("signal_type") or detail.get("category") or "human_intelligence_signal").strip().lower().replace(" ", "_")
            parameter_name = str(detail.get("summary") or detail.get("signal_type") or "Human intelligence signal")
            source = str(detail.get("source") or "Human Intelligence")
            source_type = "HUMAN_INTELLIGENCE"
            source_url = str(detail.get("raw_url") or "")
            collected_at = _parse_datetime(detail.get("collection_timestamp")) or profile.updated_at or _now()
            verified_at = collected_at
            value_text = _normalize_value(detail.get("summary") or detail.get("polarity") or "signal")
            verification_status = "PARTIALLY_VERIFIED"
            dedup_key = _stable_hash(profile.facility_id, parameter_id, value_text, source_type, source_url)
            evidence_id = f"evh-{_stable_hash('human', profile.facility_id, index, source, collected_at.isoformat())[:20]}"

            items.append(
                NormalizedEvidenceItem(
                    evidence_id=evidence_id,
                    facility_id=profile.facility_id,
                    parameter_id=parameter_id,
                    parameter_name=parameter_name,
                    parameter_value=value_text,
                    source=source,
                    source_type=source_type,
                    source_url=source_url,
                    collection_method="intelligence_signal_collection",
                    collected_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                    verified_at=verified_at if verified_at.tzinfo else verified_at.replace(tzinfo=timezone.utc),
                    verification_status=verification_status,
                    confidence_score=_base_confidence(source_type, verification_status),
                    importance_score=_importance_score(parameter_id, registry_index),
                    expires_at=_expires_at(verified_at, source_type, parameter_id),
                    runtime_version=runtime_version,
                    connector="HUMAN_INTELLIGENCE",
                    affects_recommendation=False,
                    dedup_group_key=dedup_key,
                    raw_payload=detail,
                )
            )

    outcomes = db.query(ResidentOutcome).all()
    for row in outcomes:
        if row.facility_id is None:
            continue
        collected_at = row.recorded_at or _now()
        for parameter_id, value in {
            "outcome_successful_adjustment": int(row.successful_adjustment),
            "outcome_loneliness_event": int(row.loneliness_event),
            "outcome_relocated_within_24m": int(row.relocated_within_24m),
        }.items():
            parameter_name = parameter_id.replace("_", " ")
            value_text = _normalize_value(value)
            verification_status = "VERIFIED"
            source_type = "RESIDENT_OUTCOMES"
            source = "Resident outcomes"
            dedup_key = _stable_hash(row.facility_id, parameter_id, value_text, source_type, row.id)
            evidence_id = f"evo-{_stable_hash('outcome', row.id, parameter_id)[:20]}"

            items.append(
                NormalizedEvidenceItem(
                    evidence_id=evidence_id,
                    facility_id=row.facility_id,
                    parameter_id=parameter_id,
                    parameter_name=parameter_name,
                    parameter_value=value_text,
                    source=source,
                    source_type=source_type,
                    source_url="",
                    collection_method="resident_outcome_capture",
                    collected_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                    verified_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                    verification_status=verification_status,
                    confidence_score=_base_confidence(source_type, verification_status),
                    importance_score=_importance_score(parameter_id, registry_index),
                    expires_at=_expires_at(collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc), source_type, parameter_id),
                    runtime_version=runtime_version,
                    connector="RESIDENT_OUTCOMES",
                    affects_recommendation=False,
                    dedup_group_key=dedup_key,
                    raw_payload={"resident_key": row.resident_key, "notes": row.notes},
                )
            )

    reviews = db.query(FacilityReview).all()
    for row in reviews:
        collected_at = row.created_at or _now()
        value_text = _normalize_value(row.rating)
        parameter_id = "family_review_rating"
        dedup_key = _stable_hash(row.facility_id, parameter_id, value_text, row.source, row.reviewer_hash)
        evidence_id = f"evr-{_stable_hash('review', row.id)[:20]}"

        items.append(
            NormalizedEvidenceItem(
                evidence_id=evidence_id,
                facility_id=row.facility_id,
                parameter_id=parameter_id,
                parameter_name="Family review rating",
                parameter_value=value_text,
                source=row.source,
                source_type="MANUAL_RESEARCH",
                source_url="",
                collection_method="review_ingestion",
                collected_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                verified_at=collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc),
                verification_status="PARTIALLY_VERIFIED",
                confidence_score=_base_confidence("MANUAL_RESEARCH", "PARTIALLY_VERIFIED"),
                importance_score=_importance_score(parameter_id, registry_index),
                expires_at=_expires_at(collected_at if collected_at.tzinfo else collected_at.replace(tzinfo=timezone.utc), "MANUAL_RESEARCH", parameter_id),
                runtime_version=runtime_version,
                connector="MANUAL_RESEARCH",
                affects_recommendation=False,
                dedup_group_key=dedup_key,
                raw_payload={"review_text": row.review_text, "sentiment_score": row.sentiment_score},
            )
        )

    return items


def _merge_duplicates(items: Iterable[NormalizedEvidenceItem]) -> List[NormalizedEvidenceItem]:
    merged: Dict[str, NormalizedEvidenceItem] = {}
    merged_ids: Dict[str, List[str]] = {}
    source_history: Dict[str, List[Dict[str, str]]] = {}

    for item in items:
        existing = merged.get(item.dedup_group_key)
        source_stamp = {
            "source": item.source,
            "source_type": item.source_type,
            "source_url": item.source_url,
        }
        if existing is None:
            merged[item.dedup_group_key] = item
            merged_ids[item.dedup_group_key] = [item.evidence_id]
            source_history[item.dedup_group_key] = [source_stamp]
            continue

        merged_ids[item.dedup_group_key].append(item.evidence_id)
        source_history[item.dedup_group_key].append(source_stamp)

        # Keep the strongest confidence and latest verification for duplicate merges.
        if item.confidence_score > existing.confidence_score:
            existing.confidence_score = item.confidence_score
            existing.source = item.source
            existing.source_type = item.source_type
            existing.source_url = item.source_url
        if item.verified_at and (existing.verified_at is None or item.verified_at > existing.verified_at):
            existing.verified_at = item.verified_at
            existing.collected_at = item.collected_at
            existing.expires_at = item.expires_at
        if item.verification_status == "VERIFIED":
            existing.verification_status = "VERIFIED"

    result: List[NormalizedEvidenceItem] = []
    for key, item in merged.items():
        raw_payload = dict(item.raw_payload)
        raw_payload["merged_from"] = merged_ids.get(key, [])
        raw_payload["source_history"] = source_history.get(key, [])
        item.raw_payload = raw_payload
        result.append(item)
    return result


def _source_rank(source_type: str) -> int:
    order = [
        "CMS",
        "CMS_NURSING_HOME_COMPARE",
        "STATE_INSPECTIONS",
        "RESIDENT_OUTCOMES",
        "FACILITY_PORTAL",
        "MANUAL_RESEARCH",
        "HUMAN_INTELLIGENCE",
        "EXTERNAL_DISCOVERY",
        "UNKNOWN",
    ]
    try:
        return len(order) - order.index(source_type)
    except ValueError:
        return 1


def _mark_conflicts_and_preferred(items: List[NormalizedEvidenceItem]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[Tuple[Optional[int], str], List[NormalizedEvidenceItem]] = {}
    for item in items:
        grouped.setdefault((item.facility_id, item.parameter_id), []).append(item)

    resolved: Dict[str, Dict[str, Any]] = {}
    for key, rows in grouped.items():
        normalized_values = {str(row.parameter_value).upper() for row in rows if row.parameter_value not in {None, "", "UNKNOWN"}}
        has_conflict = len(normalized_values) > 1

        preferred = sorted(
            rows,
            key=lambda row: (
                1 if row.verification_status in VERIFIED_STATUSES else 0,
                row.confidence_score,
                _source_rank(row.source_type),
                row.verified_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
            ),
            reverse=True,
        )[0]

        for row in rows:
            resolved[row.evidence_id] = {
                "conflict_status": "CONFLICT" if has_conflict else "NO_CONFLICT",
                "preferred": row.evidence_id == preferred.evidence_id,
            }

    return resolved


def _snapshot_payload(item: NormalizedEvidenceItem, conflict_status: str, preferred: bool) -> Dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "facility_id": item.facility_id,
        "parameter_id": item.parameter_id,
        "parameter_name": item.parameter_name,
        "parameter_value": item.parameter_value,
        "source": item.source,
        "source_type": item.source_type,
        "source_url": item.source_url,
        "collection_method": item.collection_method,
        "collected_at": item.collected_at.isoformat(),
        "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        "verification_status": item.verification_status,
        "confidence_score": round(item.confidence_score, 4),
        "importance_score": round(item.importance_score, 2),
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "runtime_version": item.runtime_version,
        "connector": item.connector,
        "conflict_status": conflict_status,
        "preferred": preferred,
        "affects_recommendation": item.affects_recommendation,
        "dedup_group_key": item.dedup_group_key,
        "raw_payload": item.raw_payload,
    }


def _upsert_registry_items(db: Session, items: List[NormalizedEvidenceItem]) -> Dict[str, int]:
    existing_rows = {row.evidence_id: row for row in db.query(FacilityEvidenceRegistry).all()}
    conflict_map = _mark_conflicts_and_preferred(items)

    created = 0
    updated = 0
    unchanged = 0
    seen_ids = set()

    for item in items:
        seen_ids.add(item.evidence_id)
        conflict = conflict_map.get(item.evidence_id, {"conflict_status": "NO_CONFLICT", "preferred": False})
        snapshot = _snapshot_payload(item, conflict["conflict_status"], bool(conflict["preferred"]))
        snapshot_text = json.dumps(snapshot, sort_keys=True, default=str)

        row = existing_rows.get(item.evidence_id)
        if row is None:
            db.add(
                FacilityEvidenceRegistry(
                    evidence_id=item.evidence_id,
                    facility_id=item.facility_id,
                    parameter_id=item.parameter_id,
                    parameter_name=item.parameter_name,
                    parameter_value=item.parameter_value,
                    source=item.source,
                    source_type=item.source_type,
                    source_url=item.source_url,
                    collection_method=item.collection_method,
                    collected_at=item.collected_at,
                    verified_at=item.verified_at,
                    verification_status=item.verification_status,
                    confidence_score=item.confidence_score,
                    importance_score=item.importance_score,
                    expires_at=item.expires_at,
                    runtime_version=item.runtime_version,
                    connector=item.connector,
                    conflict_status=conflict["conflict_status"],
                    preferred=bool(conflict["preferred"]),
                    affects_recommendation=item.affects_recommendation,
                    dedup_group_key=item.dedup_group_key,
                    merged_from_json=json.dumps(item.raw_payload.get("merged_from") or []),
                    source_history_json=json.dumps(item.raw_payload.get("source_history") or []),
                    raw_payload_json=json.dumps(item.raw_payload, default=str),
                    current_version=1,
                    last_seen_at=_now(),
                )
            )
            db.add(
                FacilityEvidenceRegistryVersion(
                    evidence_id=item.evidence_id,
                    version_number=1,
                    action="CREATED",
                    snapshot_json=snapshot_text,
                )
            )
            created += 1
            continue

        previous_snapshot = {
            "parameter_value": row.parameter_value,
            "source": row.source,
            "source_type": row.source_type,
            "verification_status": row.verification_status,
            "confidence_score": round(float(row.confidence_score or 0.0), 4),
            "importance_score": round(float(row.importance_score or 0.0), 2),
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "conflict_status": row.conflict_status,
            "preferred": bool(row.preferred),
        }
        current_snapshot = {
            "parameter_value": item.parameter_value,
            "source": item.source,
            "source_type": item.source_type,
            "verification_status": item.verification_status,
            "confidence_score": round(float(item.confidence_score), 4),
            "importance_score": round(float(item.importance_score), 2),
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "conflict_status": conflict["conflict_status"],
            "preferred": bool(conflict["preferred"]),
        }

        if previous_snapshot == current_snapshot:
            row.last_seen_at = _now()
            unchanged += 1
            continue

        row.parameter_name = item.parameter_name
        row.parameter_value = item.parameter_value
        row.source = item.source
        row.source_type = item.source_type
        row.source_url = item.source_url
        row.collection_method = item.collection_method
        row.collected_at = item.collected_at
        row.verified_at = item.verified_at
        row.verification_status = item.verification_status
        row.confidence_score = item.confidence_score
        row.importance_score = item.importance_score
        row.expires_at = item.expires_at
        row.runtime_version = item.runtime_version
        row.connector = item.connector
        row.conflict_status = conflict["conflict_status"]
        row.preferred = bool(conflict["preferred"])
        row.affects_recommendation = item.affects_recommendation
        row.dedup_group_key = item.dedup_group_key
        row.merged_from_json = json.dumps(item.raw_payload.get("merged_from") or [])
        row.source_history_json = json.dumps(item.raw_payload.get("source_history") or [])
        row.raw_payload_json = json.dumps(item.raw_payload, default=str)
        row.current_version = int(row.current_version or 1) + 1
        row.last_seen_at = _now()

        db.add(
            FacilityEvidenceRegistryVersion(
                evidence_id=item.evidence_id,
                version_number=row.current_version,
                action="UPDATED",
                snapshot_json=snapshot_text,
            )
        )
        updated += 1

    # Retire rows not seen in the refresh, keeping immutable history.
    for row in existing_rows.values():
        if row.evidence_id in seen_ids:
            continue
        if row.verification_status == "RETIRED":
            continue
        row.current_version = int(row.current_version or 1) + 1
        row.verification_status = "RETIRED"
        row.preferred = False
        row.last_seen_at = _now()
        db.add(
            FacilityEvidenceRegistryVersion(
                evidence_id=row.evidence_id,
                version_number=row.current_version,
                action="RETIRED",
                snapshot_json=json.dumps({
                    "evidence_id": row.evidence_id,
                    "verification_status": "RETIRED",
                }),
            )
        )
        updated += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "total": len(items),
    }


def refresh_evidence_registry(db: Session) -> Dict[str, Any]:
    runtime_meta = get_runtime_metadata()
    runtime_version = str(runtime_meta.get("runtime_version") or "unknown")
    registry_index = _parameter_registry_index()

    items: List[NormalizedEvidenceItem] = []
    items.extend(_normalize_from_parameter_runtime(db, runtime_version, registry_index))
    items.extend(_normalize_from_facility_portal(db, runtime_version, registry_index))
    items.extend(_normalize_from_inspections(db, runtime_version, registry_index))
    items.extend(_normalize_from_human_and_outcomes(db, runtime_version, registry_index))

    deduped = _merge_duplicates(items)
    write_result = _upsert_registry_items(db, deduped)

    return {
        "runtime_version": runtime_version,
        "runtime_timestamp": runtime_meta.get("runtime_timestamp"),
        "normalized_count": len(items),
        "deduplicated_count": len(deduped),
        **write_result,
    }


def _facility_coverage_rows(db: Session) -> List[Dict[str, Any]]:
    registry_index = _parameter_registry_index()
    parameter_ids = list(registry_index.keys())
    critical_ids = {
        key
        for key, row in registry_index.items()
        if bool(row.get("hard_filter_eligibility")) or bool(row.get("ranking_eligibility"))
    }

    rows = db.query(FacilityEvidenceRegistry).filter(FacilityEvidenceRegistry.verification_status != "RETIRED").all()
    by_facility: Dict[int, Dict[str, FacilityEvidenceRegistry]] = {}
    for row in rows:
        if row.facility_id is None:
            continue
        current = by_facility.setdefault(int(row.facility_id), {})
        if not row.preferred:
            continue
        current[row.parameter_id] = row

    facilities = db.query(Facility.id, Facility.name, Facility.city, Facility.state).filter(Facility.state == "FL").all()
    result: List[Dict[str, Any]] = []

    for facility in facilities:
        evidence_map = by_facility.get(int(facility.id), {})
        known_ids = {
            pid
            for pid, row in evidence_map.items()
            if row.verification_status in VERIFIED_STATUSES and str(row.parameter_value or "").upper() not in {"", "UNKNOWN", "NOT VERIFIED"}
        }
        unknown_ids = set(parameter_ids) - known_ids
        critical_missing = sorted(critical_ids.intersection(unknown_ids))
        known_count = len(known_ids)
        unknown_count = len(unknown_ids)
        total = len(parameter_ids) if parameter_ids else 1
        coverage_pct = round((known_count / total) * 100.0, 2)

        freshness_known = 0
        for pid in known_ids:
            row = evidence_map.get(pid)
            if row is None:
                continue
            if row.expires_at is None or row.expires_at >= _now():
                freshness_known += 1
        freshness_pct = round((freshness_known / max(1, known_count)) * 100.0, 2) if known_count else 0.0

        conflicts = sum(1 for row in evidence_map.values() if row.conflict_status == "CONFLICT")
        consistency_pct = round(max(0.0, 100.0 - (conflicts * 100.0 / max(1, len(evidence_map)))), 2)

        quality_score = round(
            (coverage_pct * 0.35)
            + (freshness_pct * 0.25)
            + (consistency_pct * 0.2)
            + (sum(float(evidence_map[pid].confidence_score) for pid in known_ids) / max(1, known_count) * 100.0 * 0.2),
            2,
        )

        result.append(
            {
                "facility_id": int(facility.id),
                "facility_name": facility.name,
                "city": facility.city,
                "state": facility.state,
                "known_parameters": known_count,
                "unknown_parameters": unknown_count,
                "coverage_pct": coverage_pct,
                "critical_missing_parameters": critical_missing,
                "evidence_freshness_pct": freshness_pct,
                "evidence_quality_score": quality_score,
            }
        )

    result.sort(key=lambda item: item["coverage_pct"], reverse=True)
    return result


def _validation_report(db: Session) -> Dict[str, Any]:
    active_rows = db.query(FacilityEvidenceRegistry).filter(FacilityEvidenceRegistry.verification_status != "RETIRED").all()

    duplicate_groups: Dict[str, int] = {}
    for row in active_rows:
        duplicate_groups[row.dedup_group_key] = duplicate_groups.get(row.dedup_group_key, 0) + 1
    duplicate_count = sum(1 for value in duplicate_groups.values() if value > 1)

    orphans = [row.evidence_id for row in active_rows if row.facility_id is None]

    registry_index = _parameter_registry_index()
    recommendation_parameter_ids = {
        key
        for key, value in registry_index.items()
        if bool(value.get("ranking_eligibility")) or bool(value.get("hard_filter_eligibility"))
    }

    preferred_rows = [row for row in active_rows if row.preferred]
    evidence_parameter_ids = {row.parameter_id for row in preferred_rows}
    missing_recommendation_parameter_evidence = sorted(recommendation_parameter_ids - evidence_parameter_ids)

    unknown_preserved = all(
        row.verification_status == "UNKNOWN"
        for row in preferred_rows
        if str(row.parameter_value or "").upper() in {"UNKNOWN", "", "NOT VERIFIED"}
    )

    return {
        "no_duplicate_evidence": duplicate_count == 0,
        "no_orphan_evidence": len(orphans) == 0,
        "every_recommendation_parameter_references_evidence": len(missing_recommendation_parameter_evidence) == 0,
        "unknown_is_preserved": unknown_preserved,
        "duplicate_group_count": duplicate_count,
        "orphan_evidence_ids": orphans[:100],
        "missing_recommendation_parameter_evidence": missing_recommendation_parameter_evidence,
    }


def get_evidence_status(db: Session) -> Dict[str, Any]:
    rows = db.query(FacilityEvidenceRegistry).filter(FacilityEvidenceRegistry.verification_status != "RETIRED").all()
    conflicts = sum(1 for row in rows if row.conflict_status == "CONFLICT")
    preferred = sum(1 for row in rows if row.preferred)

    connector_counts: Dict[str, int] = {}
    source_type_counts: Dict[str, int] = {}
    for row in rows:
        connector_counts[row.connector] = connector_counts.get(row.connector, 0) + 1
        source_type_counts[row.source_type] = source_type_counts.get(row.source_type, 0) + 1

    validation = _validation_report(db)
    return {
        "total_evidence_items": len(rows),
        "preferred_evidence_items": preferred,
        "conflict_items": conflicts,
        "connector_counts": connector_counts,
        "source_type_counts": source_type_counts,
        "validation": validation,
    }


def get_evidence_for_facility(
    db: Session,
    facility_id: int,
    *,
    parameter_id: Optional[str] = None,
    verification_status: Optional[str] = None,
    conflicts_only: bool = False,
    include_non_preferred: bool = False,
) -> Dict[str, Any]:
    query = db.query(FacilityEvidenceRegistry).filter(
        FacilityEvidenceRegistry.facility_id == facility_id,
        FacilityEvidenceRegistry.verification_status != "RETIRED",
    )
    if not include_non_preferred:
        query = query.filter(FacilityEvidenceRegistry.preferred == True)  # noqa: E712
    if parameter_id:
        query = query.filter(FacilityEvidenceRegistry.parameter_id == parameter_id)
    if verification_status:
        query = query.filter(FacilityEvidenceRegistry.verification_status == verification_status)
    if conflicts_only:
        query = query.filter(FacilityEvidenceRegistry.conflict_status == "CONFLICT")

    rows = query.order_by(FacilityEvidenceRegistry.importance_score.desc(), FacilityEvidenceRegistry.verified_at.desc().nullslast()).all()

    items = []
    for row in rows:
        items.append(
            {
                "evidence_id": row.evidence_id,
                "facility_id": row.facility_id,
                "parameter_id": row.parameter_id,
                "parameter_name": row.parameter_name,
                "parameter_value": row.parameter_value,
                "source": row.source,
                "source_type": row.source_type,
                "source_url": row.source_url,
                "collection_method": row.collection_method,
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
                "verified_at": row.verified_at.isoformat() if row.verified_at else None,
                "verification_status": row.verification_status,
                "confidence_score": row.confidence_score,
                "importance_score": row.importance_score,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "runtime_version": row.runtime_version,
                "connector": row.connector,
                "conflict_status": row.conflict_status,
                "preferred": bool(row.preferred),
                "affects_recommendation": bool(row.affects_recommendation),
                "source_history": json.loads(row.source_history_json or "[]"),
                "merged_from": json.loads(row.merged_from_json or "[]"),
            }
        )

    return {
        "facility_id": facility_id,
        "evidence_count": len(items),
        "items": items,
    }


def get_evidence_history(db: Session, facility_id: int, limit: int = 500) -> Dict[str, Any]:
    evidence_ids = [
        row.evidence_id
        for row in db.query(FacilityEvidenceRegistry.evidence_id)
        .filter(FacilityEvidenceRegistry.facility_id == facility_id)
        .all()
    ]
    if not evidence_ids:
        return {"facility_id": facility_id, "history_count": 0, "history": []}

    rows = (
        db.query(FacilityEvidenceRegistryVersion)
        .filter(FacilityEvidenceRegistryVersion.evidence_id.in_(evidence_ids))
        .order_by(FacilityEvidenceRegistryVersion.created_at.desc())
        .limit(limit)
        .all()
    )

    history = [
        {
            "evidence_id": row.evidence_id,
            "version_number": row.version_number,
            "action": row.action,
            "snapshot": json.loads(row.snapshot_json or "{}"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return {
        "facility_id": facility_id,
        "history_count": len(history),
        "history": history,
    }


def get_evidence_coverage(db: Session, facility_id: Optional[int] = None) -> Dict[str, Any]:
    rows = _facility_coverage_rows(db)
    if facility_id is not None:
        rows = [row for row in rows if row["facility_id"] == facility_id]
    overall = {
        "facility_count": len(rows),
        "average_coverage_pct": round(sum(row["coverage_pct"] for row in rows) / max(1, len(rows)), 2),
        "average_freshness_pct": round(sum(row["evidence_freshness_pct"] for row in rows) / max(1, len(rows)), 2),
        "average_quality_score": round(sum(row["evidence_quality_score"] for row in rows) / max(1, len(rows)), 2),
    }
    return {"overall": overall, "facilities": rows}


def search_evidence_registry(
    db: Session,
    *,
    q: str = "",
    source_type: Optional[str] = None,
    verification_status: Optional[str] = None,
    conflicts_only: bool = False,
    missing_only: bool = False,
    facility_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    query = db.query(FacilityEvidenceRegistry).filter(FacilityEvidenceRegistry.verification_status != "RETIRED")

    if facility_id is not None:
        query = query.filter(FacilityEvidenceRegistry.facility_id == facility_id)
    if source_type:
        query = query.filter(FacilityEvidenceRegistry.source_type == source_type)
    if verification_status:
        query = query.filter(FacilityEvidenceRegistry.verification_status == verification_status)
    if conflicts_only:
        query = query.filter(FacilityEvidenceRegistry.conflict_status == "CONFLICT")
    if missing_only:
        query = query.filter(FacilityEvidenceRegistry.verification_status == "UNKNOWN")

    term = (q or "").strip().lower()
    if term:
        like = f"%{term}%"
        query = query.filter(
            (FacilityEvidenceRegistry.parameter_id.ilike(like))
            | (FacilityEvidenceRegistry.parameter_name.ilike(like))
            | (FacilityEvidenceRegistry.source.ilike(like))
            | (FacilityEvidenceRegistry.source_type.ilike(like))
        )

    total = query.count()
    rows = (
        query.order_by(FacilityEvidenceRegistry.importance_score.desc(), FacilityEvidenceRegistry.verified_at.desc().nullslast())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 1000)))
        .all()
    )

    items = [
        {
            "evidence_id": row.evidence_id,
            "facility_id": row.facility_id,
            "parameter_id": row.parameter_id,
            "parameter_name": row.parameter_name,
            "parameter_value": row.parameter_value,
            "source": row.source,
            "source_type": row.source_type,
            "verification_status": row.verification_status,
            "confidence_score": row.confidence_score,
            "importance_score": row.importance_score,
            "conflict_status": row.conflict_status,
            "preferred": bool(row.preferred),
            "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }
        for row in rows
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
