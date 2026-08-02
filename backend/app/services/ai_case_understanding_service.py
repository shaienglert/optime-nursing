from __future__ import annotations

import json
import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.patient_profile import PatientProfile, PatientProfileVersion

REPO_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_PATH = REPO_ROOT / "database" / "ai_case_understanding_ontology.json"

AGE_RE = re.compile(r"\b(?:age\s*)?(\d{2,3})\b", re.IGNORECASE)
BUDGET_RE = re.compile(r"(?:\$|usd\s*)?([1-9]\d{0,2}(?:,\d{3})+|[1-9]\d{3,5}|[1-9](?:\.\d+)?)\s*(k|thousand)?", re.IGNORECASE)
CITY_PATTERN_RE = re.compile(r"\b(?:in|near|around|from|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)")


@dataclass
class FieldExtraction:
    value: Any
    confidence: float
    source_sentence: str
    needs_review: bool


@dataclass
class CaseUnderstandingResult:
    structured_profile: Dict[str, Dict[str, Any]]
    missing_critical_fields: List[str]
    follow_up_questions: List[str]
    ambiguity_notes: List[Dict[str, Any]]
    case_summary: str
    questionnaire_state: Dict[str, Any]
    decision_handoff: Dict[str, Any]
    profile_confidence: float


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def _ontology() -> Dict[str, Any]:
    if not ONTOLOGY_PATH.exists():
        return {"fields": {}, "critical_fields": [], "follow_up_questions": {}, "ambiguity_markers": []}
    payload = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {"fields": {}, "critical_fields": [], "follow_up_questions": {}, "ambiguity_markers": []}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9']+", _normalize_text(text))


def _split_sentences(text: str) -> List[str]:
    rows = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    return rows if rows else [text.strip()] if text.strip() else []


def _sentence_score(sentence: str, alias: str) -> float:
    sentence_tokens = set(_tokens(sentence))
    alias_tokens = set(_tokens(alias))
    if not alias_tokens:
        return 0.0
    overlap = len(sentence_tokens.intersection(alias_tokens)) / len(alias_tokens)
    substring = 1.0 if _normalize_text(alias) in _normalize_text(sentence) else 0.0
    coverage = len(sentence_tokens.intersection(alias_tokens)) / max(1, len(sentence_tokens))
    return (overlap * 0.6) + (substring * 0.3) + (coverage * 0.1)


def _ambiguity_multiplier(sentence: str, ambiguity_markers: Sequence[str]) -> Tuple[float, List[str]]:
    lowered = _normalize_text(sentence)
    hits = [marker for marker in ambiguity_markers if marker in lowered]
    if not hits:
        return 1.0, []
    penalty = max(0.55, 1.0 - (0.12 * len(hits)))
    return penalty, hits


def _extract_age(sentences: Sequence[str], ambiguity_markers: Sequence[str]) -> FieldExtraction:
    best_value: Optional[int] = None
    best_conf = 0.0
    best_sentence = ""
    for sentence in sentences:
        match = AGE_RE.search(sentence)
        if not match:
            continue
        value = int(match.group(1))
        if value < 55 or value > 110:
            continue
        penalty, _ = _ambiguity_multiplier(sentence, ambiguity_markers)
        confidence = min(0.98, 0.84 * penalty + 0.14)
        if confidence > best_conf:
            best_value = value
            best_conf = confidence
            best_sentence = sentence

    if best_value is None:
        return FieldExtraction(value=None, confidence=0.0, source_sentence="", needs_review=True)

    return FieldExtraction(value=best_value, confidence=round(best_conf, 3), source_sentence=best_sentence, needs_review=best_conf < 0.7)


def _extract_budget(sentences: Sequence[str], ambiguity_markers: Sequence[str]) -> FieldExtraction:
    best_value: Optional[int] = None
    best_conf = 0.0
    best_sentence = ""

    for sentence in sentences:
        lowered = _normalize_text(sentence)
        if "budget" not in lowered and "$" not in sentence and "usd" not in lowered:
            continue
        for match in BUDGET_RE.finditer(sentence):
            amount_text = match.group(1).replace(",", "")
            amount = float(amount_text)
            suffix = (match.group(2) or "").lower()
            if suffix == "k":
                amount *= 1000
            if suffix == "thousand":
                amount *= 1000
            budget = int(round(amount))
            if budget < 500 or budget > 50000:
                continue
            penalty, _ = _ambiguity_multiplier(sentence, ambiguity_markers)
            confidence = min(0.98, 0.86 * penalty + 0.12)
            if confidence > best_conf:
                best_conf = confidence
                best_value = budget
                best_sentence = sentence

    if best_value is None:
        return FieldExtraction(value=None, confidence=0.0, source_sentence="", needs_review=True)

    return FieldExtraction(value=best_value, confidence=round(best_conf, 3), source_sentence=best_sentence, needs_review=best_conf < 0.72)


def _extract_location(sentences: Sequence[str], city_index: Sequence[str], ambiguity_markers: Sequence[str]) -> FieldExtraction:
    city_candidates = [city.strip() for city in city_index if city and city.strip()]
    city_lookup = {city.lower(): city for city in city_candidates}

    best_city: Optional[str] = None
    best_conf = 0.0
    best_sentence = ""

    for sentence in sentences:
        lowered = _normalize_text(sentence)
        penalty, _ = _ambiguity_multiplier(sentence, ambiguity_markers)

        for city in city_candidates:
            city_norm = city.lower()
            if city_norm and city_norm in lowered:
                confidence = min(0.98, 0.9 * penalty + 0.07)
                if confidence > best_conf:
                    best_city = city_lookup[city_norm]
                    best_conf = confidence
                    best_sentence = sentence

        for match in CITY_PATTERN_RE.finditer(sentence):
            candidate = match.group(1).strip()
            candidate_norm = candidate.lower()
            if candidate_norm in city_lookup:
                confidence = min(0.95, 0.84 * penalty + 0.08)
                if confidence > best_conf:
                    best_city = city_lookup[candidate_norm]
                    best_conf = confidence
                    best_sentence = sentence

    if best_city is None:
        return FieldExtraction(value=None, confidence=0.0, source_sentence="", needs_review=True)

    return FieldExtraction(value=best_city, confidence=round(best_conf, 3), source_sentence=best_sentence, needs_review=best_conf < 0.72)


def _extract_single_field(
    field_name: str,
    sentences: Sequence[str],
    ontology_field: Dict[str, List[str]],
    ambiguity_markers: Sequence[str],
) -> FieldExtraction:
    best_value: Optional[str] = None
    best_score = 0.0
    best_sentence = ""

    for sentence in sentences:
        penalty, _ = _ambiguity_multiplier(sentence, ambiguity_markers)
        for canonical_value, aliases in ontology_field.items():
            aliases_all = list(aliases or []) + [canonical_value.replace("_", " ")]
            score = max((_sentence_score(sentence, alias) for alias in aliases_all), default=0.0)
            score = score * penalty
            if score > best_score:
                best_score = score
                best_value = canonical_value
                best_sentence = sentence

    if best_value is None or best_score < 0.42:
        return FieldExtraction(value=None, confidence=0.0, source_sentence="", needs_review=True)

    confidence = min(0.98, 0.45 + (best_score * 0.55))
    return FieldExtraction(value=best_value, confidence=round(confidence, 3), source_sentence=best_sentence, needs_review=confidence < 0.7)


def _extract_multi_field(
    field_name: str,
    sentences: Sequence[str],
    ontology_field: Dict[str, List[str]],
    ambiguity_markers: Sequence[str],
) -> FieldExtraction:
    matches: List[Tuple[str, float, str]] = []

    for canonical_value, aliases in ontology_field.items():
        best_score = 0.0
        best_sentence = ""
        for sentence in sentences:
            penalty, _ = _ambiguity_multiplier(sentence, ambiguity_markers)
            aliases_all = list(aliases or []) + [canonical_value.replace("_", " ")]
            score = max((_sentence_score(sentence, alias) for alias in aliases_all), default=0.0)
            score = score * penalty
            if score > best_score:
                best_score = score
                best_sentence = sentence

        if best_score >= 0.5:
            confidence = min(0.97, 0.42 + (best_score * 0.58))
            matches.append((canonical_value, round(confidence, 3), best_sentence))

    if not matches:
        return FieldExtraction(value=[], confidence=0.0, source_sentence="", needs_review=True)

    matches_sorted = sorted(matches, key=lambda item: item[1], reverse=True)
    values = [item[0] for item in matches_sorted]
    confidence = round(mean(item[1] for item in matches_sorted), 3)
    source_sentence = matches_sorted[0][2]
    return FieldExtraction(value=values, confidence=confidence, source_sentence=source_sentence, needs_review=confidence < 0.7)


def _build_profile_fields(db: Session, case_text: str) -> Tuple[Dict[str, FieldExtraction], List[Dict[str, Any]]]:
    ontology = _ontology()
    fields = ontology.get("fields") or {}
    ambiguity_markers = ontology.get("ambiguity_markers") or []
    sentences = _split_sentences(case_text)

    ambiguity_notes: List[Dict[str, Any]] = []
    for sentence in sentences:
        multiplier, hits = _ambiguity_multiplier(sentence, ambiguity_markers)
        if hits:
            ambiguity_notes.append(
                {
                    "sentence": sentence,
                    "markers": hits,
                    "confidence_multiplier": round(multiplier, 3),
                }
            )

    city_rows = db.query(Facility.city).filter(Facility.state == "FL").all()
    city_index = sorted({str(row.city).strip() for row in city_rows if row.city})

    extracted: Dict[str, FieldExtraction] = {
        "age": _extract_age(sentences, ambiguity_markers),
        "gender": _extract_single_field("gender", sentences, fields.get("gender") or {}, ambiguity_markers),
        "diagnosis": _extract_multi_field("diagnosis", sentences, fields.get("diagnosis") or {}, ambiguity_markers),
        "cognitive_status": _extract_single_field("cognitive_status", sentences, fields.get("cognitive_status") or {}, ambiguity_markers),
        "mobility": _extract_single_field("mobility", sentences, fields.get("mobility") or {}, ambiguity_markers),
        "adl": _extract_multi_field("adl", sentences, fields.get("adl") or {}, ambiguity_markers),
        "medical_conditions": _extract_multi_field("medical_conditions", sentences, fields.get("diagnosis") or {}, ambiguity_markers),
        "behavior": _extract_multi_field("behavior", sentences, fields.get("behavior") or {}, ambiguity_markers),
        "languages": _extract_multi_field("languages", sentences, fields.get("languages") or {}, ambiguity_markers),
        "religion": _extract_single_field("religion", sentences, fields.get("religion") or {}, ambiguity_markers),
        "budget": _extract_budget(sentences, ambiguity_markers),
        "location": _extract_location(sentences, city_index, ambiguity_markers),
        "lifestyle": _extract_multi_field("lifestyle", sentences, fields.get("lifestyle") or {}, ambiguity_markers),
        "activities": _extract_multi_field("activities", sentences, fields.get("activities") or {}, ambiguity_markers),
        "personality": _extract_multi_field("personality", sentences, fields.get("personality") or {}, ambiguity_markers),
        "social_preferences": _extract_multi_field("social_preferences", sentences, fields.get("social_preferences") or {}, ambiguity_markers),
        "family_preferences": _extract_multi_field("family_preferences", sentences, fields.get("family_preferences") or {}, ambiguity_markers),
        "transportation": _extract_multi_field("transportation", sentences, fields.get("transportation") or {}, ambiguity_markers),
        "special_requests": _extract_multi_field("special_requests", sentences, fields.get("special_requests") or {}, ambiguity_markers),
    }

    return extracted, ambiguity_notes


def _to_serialized_fields(extracted: Dict[str, FieldExtraction]) -> Dict[str, Dict[str, Any]]:
    return {
        key: {
            "value": value.value,
            "confidence": round(float(value.confidence), 3),
            "source_sentence": value.source_sentence,
            "needs_review": bool(value.needs_review),
        }
        for key, value in extracted.items()
    }


def _missing_fields(structured: Dict[str, Dict[str, Any]]) -> List[str]:
    ontology = _ontology()
    critical_fields = ontology.get("critical_fields") or []
    missing: List[str] = []
    for field in critical_fields:
        node = structured.get(field) or {}
        value = node.get("value")
        confidence = float(node.get("confidence") or 0.0)
        needs_review = bool(node.get("needs_review"))

        is_empty = value in (None, "", [])
        if is_empty or confidence < 0.55 or (needs_review and confidence < 0.7):
            missing.append(field)
    return sorted(set(missing))


def _follow_up_questions(structured: Dict[str, Dict[str, Any]], missing_fields: Sequence[str]) -> List[str]:
    ontology = _ontology()
    question_map = ontology.get("follow_up_questions") or {}

    followups: List[str] = []
    for field in missing_fields:
        question = question_map.get(field)
        if question and question not in followups:
            followups.append(question)

    for field, node in structured.items():
        confidence = float(node.get("confidence") or 0.0)
        value = node.get("value")
        if field in missing_fields:
            continue
        if confidence < 0.6 and value not in (None, "", []):
            question = question_map.get(field)
            if question and question not in followups:
                followups.append(question)

    return followups[:8]


def _memory_status(cognitive_status: Optional[str]) -> str:
    if cognitive_status in {"significant", "moderate"}:
        return "Significant memory support"
    if cognitive_status == "mild":
        return "Mild memory issues"
    if cognitive_status == "none":
        return "No memory issues"
    return "Not sure"


def _assistance_level(structured: Dict[str, Dict[str, Any]]) -> str:
    adl = structured.get("adl", {}).get("value") or []
    mobility = structured.get("mobility", {}).get("value")
    diagnosis = structured.get("diagnosis", {}).get("value") or []

    high_load_score = 0
    if isinstance(adl, list):
        high_load_score += min(4, len(adl))
    if mobility in {"wheelchair", "bed_bound"}:
        high_load_score += 3
    elif mobility in {"walker", "cane"}:
        high_load_score += 2
    if any(condition in {"stroke", "heart_failure", "copd", "post_surgical_recovery", "fracture_rehab"} for condition in diagnosis):
        high_load_score += 2

    if high_load_score >= 5:
        return "24/7 support required"
    if high_load_score >= 3:
        return "High assistance"
    if high_load_score >= 1:
        return "Light assistance"
    return "Light assistance"


def _preferred_language(structured: Dict[str, Dict[str, Any]]) -> str:
    languages = structured.get("languages", {}).get("value") or []
    if isinstance(languages, list) and languages:
        return str(languages[0]).title()
    return "English"


def _dietary_preferences(structured: Dict[str, Dict[str, Any]]) -> List[str]:
    special_requests = structured.get("special_requests", {}).get("value") or []
    religion = structured.get("religion", {}).get("value")

    preferences: List[str] = []
    if isinstance(special_requests, list) and "kosher_meals" in special_requests:
        preferences.append("Kosher")
    if religion == "jewish" and "Kosher" not in preferences:
        preferences.append("Kosher")
    return preferences


def _distance_from_family(structured: Dict[str, Dict[str, Any]]) -> str:
    family_pref = structured.get("family_preferences", {}).get("value") or []
    if isinstance(family_pref, list):
        if "close_distance" in family_pref:
            return "Closest to family"
        if "balanced_distance" in family_pref:
            return "Balanced location"
    return "Balanced location"


def _post_hospital_rehab_need(structured: Dict[str, Dict[str, Any]]) -> str:
    diagnosis = structured.get("diagnosis", {}).get("value") or []
    activities = structured.get("activities", {}).get("value") or []

    if any(item in {"stroke", "fracture_rehab", "post_surgical_recovery"} for item in diagnosis):
        return "yes"
    if isinstance(activities, list) and "rehab_therapy" in activities:
        return "yes"
    return "unknown"


def _questionnaire_state(case_text: str, structured: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    budget = structured.get("budget", {}).get("value")
    budget_value = int(budget) if isinstance(budget, (int, float)) else None

    return {
        "assistanceLevel": _assistance_level(structured),
        "memoryStatus": _memory_status(structured.get("cognitive_status", {}).get("value")),
        "budget": budget_value,
        "distanceFromFamily": _distance_from_family(structured),
        "humanIntelligenceV2": {
            "languageProfile": {
                "preferredSpokenLanguage": _preferred_language(structured),
            },
            "foodProfile": {
                "dietaryPreferences": _dietary_preferences(structured),
            },
            "transitionRiskProfile": {
                "postHospitalRehabNeed": _post_hospital_rehab_need(structured),
            },
        },
        "notes": case_text,
    }


def _case_summary(structured: Dict[str, Dict[str, Any]]) -> str:
    age = structured.get("age", {}).get("value")
    cognitive = structured.get("cognitive_status", {}).get("value") or "unknown"
    mobility = structured.get("mobility", {}).get("value") or "unknown"
    location = structured.get("location", {}).get("value") or "unspecified location"
    budget = structured.get("budget", {}).get("value")
    languages = structured.get("languages", {}).get("value") or []
    diagnosis = structured.get("diagnosis", {}).get("value") or []

    language_text = ", ".join(str(value).title() for value in languages[:3]) if isinstance(languages, list) and languages else "unspecified languages"
    diagnosis_text = ", ".join(str(value).replace("_", " ") for value in diagnosis[:3]) if isinstance(diagnosis, list) and diagnosis else "no major diagnosis stated"
    budget_text = f"${int(budget):,}" if isinstance(budget, (int, float)) else "unspecified budget"

    return (
        f"Case summary: {age or 'Unknown age'} year old, cognitive status {str(cognitive).replace('_', ' ')}, "
        f"mobility {str(mobility).replace('_', ' ')}, based in {location}, budget {budget_text}. "
        f"Key conditions/interests include {diagnosis_text}; language needs: {language_text}."
    )


def _profile_confidence(structured: Dict[str, Dict[str, Any]]) -> float:
    confidences = [float(node.get("confidence") or 0.0) for node in structured.values()]
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 3)


def parse_case_text(db: Session, case_text: str) -> CaseUnderstandingResult:
    extracted, ambiguity_notes = _build_profile_fields(db, case_text)
    structured = _to_serialized_fields(extracted)
    missing_critical = _missing_fields(structured)
    followups = _follow_up_questions(structured, missing_critical)
    summary = _case_summary(structured)
    questionnaire_state = _questionnaire_state(case_text, structured)
    decision_handoff = {
        "questionnaire_state": questionnaire_state,
        "natural_language_query": case_text,
    }

    return CaseUnderstandingResult(
        structured_profile=structured,
        missing_critical_fields=missing_critical,
        follow_up_questions=followups,
        ambiguity_notes=ambiguity_notes,
        case_summary=summary,
        questionnaire_state=questionnaire_state,
        decision_handoff=decision_handoff,
        profile_confidence=_profile_confidence(structured),
    )


def _persist_version(
    db: Session,
    *,
    profile: PatientProfile,
    version_number: int,
    operation: str,
    input_case_text: str,
    result: CaseUnderstandingResult,
) -> None:
    db.add(
        PatientProfileVersion(
            profile_id=profile.id,
            version_number=version_number,
            operation=operation,
            input_case_text=input_case_text,
            profile_confidence=result.profile_confidence,
            structured_profile_json=json.dumps(result.structured_profile),
            missing_fields_json=json.dumps(result.missing_critical_fields),
            follow_up_questions_json=json.dumps(result.follow_up_questions),
            ambiguity_notes_json=json.dumps(result.ambiguity_notes),
            case_summary=result.case_summary,
            questionnaire_state_json=json.dumps(result.questionnaire_state),
            decision_handoff_json=json.dumps(result.decision_handoff),
        )
    )


def _profile_payload(profile: PatientProfile) -> Dict[str, Any]:
    versions = sorted(profile.versions, key=lambda row: int(row.version_number or 0))
    return {
        "id": profile.id,
        "case_key": profile.case_key,
        "current_version": int(profile.current_version or 1),
        "profile_confidence": float(profile.profile_confidence or 0.0),
        "original_case_text": profile.original_case_text,
        "latest_case_text": profile.latest_case_text,
        "structured_profile": json.loads(profile.structured_profile_json or "{}"),
        "missing_critical_fields": json.loads(profile.missing_fields_json or "[]"),
        "follow_up_questions": json.loads(profile.follow_up_questions_json or "[]"),
        "ambiguity_notes": json.loads(profile.ambiguity_notes_json or "[]"),
        "case_summary": profile.case_summary,
        "questionnaire_state": json.loads(profile.questionnaire_state_json or "{}"),
        "decision_handoff": json.loads(profile.decision_handoff_json or "{}"),
        "created_at": _to_utc_iso(profile.created_at),
        "updated_at": _to_utc_iso(profile.updated_at),
        "versions": [
            {
                "version_number": int(version.version_number or 0),
                "operation": version.operation,
                "input_case_text": version.input_case_text,
                "profile_confidence": float(version.profile_confidence or 0.0),
                "structured_profile": json.loads(version.structured_profile_json or "{}"),
                "missing_critical_fields": json.loads(version.missing_fields_json or "[]"),
                "follow_up_questions": json.loads(version.follow_up_questions_json or "[]"),
                "ambiguity_notes": json.loads(version.ambiguity_notes_json or "[]"),
                "case_summary": version.case_summary,
                "questionnaire_state": json.loads(version.questionnaire_state_json or "{}"),
                "decision_handoff": json.loads(version.decision_handoff_json or "{}"),
                "created_at": _to_utc_iso(version.created_at),
            }
            for version in versions
        ],
    }


def understand_case(db: Session, case_text: str) -> Dict[str, Any]:
    text = (case_text or "").strip()
    if not text:
        raise ValueError("case_text is required")

    parsed = parse_case_text(db, text)
    profile = PatientProfile(
        case_key=f"case-{uuid.uuid4().hex}",
        original_case_text=text,
        latest_case_text=text,
        current_version=1,
        profile_confidence=parsed.profile_confidence,
        structured_profile_json=json.dumps(parsed.structured_profile),
        missing_fields_json=json.dumps(parsed.missing_critical_fields),
        follow_up_questions_json=json.dumps(parsed.follow_up_questions),
        ambiguity_notes_json=json.dumps(parsed.ambiguity_notes),
        case_summary=parsed.case_summary,
        questionnaire_state_json=json.dumps(parsed.questionnaire_state),
        decision_handoff_json=json.dumps(parsed.decision_handoff),
    )
    db.add(profile)
    db.flush()

    _persist_version(
        db,
        profile=profile,
        version_number=1,
        operation="UNDERSTAND",
        input_case_text=text,
        result=parsed,
    )
    db.commit()
    db.refresh(profile)
    return _profile_payload(profile)


def refine_case(db: Session, profile_id: int, refinement_text: str) -> Dict[str, Any]:
    profile = db.query(PatientProfile).filter(PatientProfile.id == profile_id).first()
    if profile is None:
        raise KeyError("Profile not found")

    text = (refinement_text or "").strip()
    if not text:
        raise ValueError("refinement_text is required")

    merged_text = f"{profile.latest_case_text.rstrip()}\n{text}".strip()
    parsed = parse_case_text(db, merged_text)
    new_version = int(profile.current_version or 1) + 1

    profile.latest_case_text = merged_text
    profile.current_version = new_version
    profile.profile_confidence = parsed.profile_confidence
    profile.structured_profile_json = json.dumps(parsed.structured_profile)
    profile.missing_fields_json = json.dumps(parsed.missing_critical_fields)
    profile.follow_up_questions_json = json.dumps(parsed.follow_up_questions)
    profile.ambiguity_notes_json = json.dumps(parsed.ambiguity_notes)
    profile.case_summary = parsed.case_summary
    profile.questionnaire_state_json = json.dumps(parsed.questionnaire_state)
    profile.decision_handoff_json = json.dumps(parsed.decision_handoff)

    _persist_version(
        db,
        profile=profile,
        version_number=new_version,
        operation="REFINE",
        input_case_text=text,
        result=parsed,
    )
    db.commit()
    db.refresh(profile)
    return _profile_payload(profile)


def get_patient_profile(db: Session, profile_id: int) -> Dict[str, Any]:
    profile = db.query(PatientProfile).filter(PatientProfile.id == profile_id).first()
    if profile is None:
        raise KeyError("Profile not found")
    return _profile_payload(profile)


def _render_case_template(case: Dict[str, Any], include_missing: Sequence[str]) -> str:
    sentences: List[str] = []
    if "age" not in include_missing:
        sentences.append(f"My {case['relationship']} is {case['age']} years old.")
    if "cognitive_status" not in include_missing:
        sentences.append(case["cognitive_sentence"])
    if "mobility" not in include_missing:
        sentences.append(case["mobility_sentence"])
    if "medical_conditions" not in include_missing:
        sentences.append(case["medical_sentence"])
    if "adl" not in include_missing:
        sentences.append(case["adl_sentence"])
    if "languages" not in include_missing:
        sentences.append(case["language_sentence"])
    if "budget" not in include_missing:
        sentences.append(case["budget_sentence"])
    if "location" not in include_missing:
        sentences.append(case["location_sentence"])
    sentences.append(case["preference_sentence"])
    return " ".join(sentences)


def _benchmark_dataset(count: int = 120) -> List[Dict[str, Any]]:
    rng = random.Random(42)
    ages = [72, 75, 79, 82, 84, 87, 90]
    relationships = ["father", "mother", "grandmother", "grandfather"]
    cognitive = [
        ("none", "He is mentally alert with no dementia."),
        ("mild", "She has mild memory issues and occasional forgetfulness."),
        ("moderate", "He has moderate dementia and needs memory support."),
        ("significant", "She has advanced dementia and severe memory impairment."),
    ]
    mobility = [
        ("independent", "She walks independently without support."),
        ("cane", "He uses a cane for mobility."),
        ("walker", "She walks with a walker."),
        ("wheelchair", "He uses a wheelchair for most movement."),
    ]
    medical = [
        (["stroke"], "He is recovering from a recent stroke."),
        (["diabetes"], "She has diabetes."),
        (["heart_failure"], "He has congestive heart failure."),
        (["copd"], "She has COPD and needs respiratory monitoring."),
    ]
    adl = [
        (["bathing", "dressing"], "Needs help with bathing and dressing."),
        (["medication"], "Requires medication management every day."),
        (["transfer"], "Needs transfer assistance for bed and chair transitions."),
    ]
    languages = [
        (["english"], "Speaks English."),
        (["english", "spanish"], "Speaks English and Spanish."),
        (["english", "hebrew"], "Speaks Hebrew and English."),
    ]
    budgets = [4200, 5500, 7000, 7500, 9000, 11000]
    locations = ["Miami", "Boca Raton", "Fort Lauderdale", "Hialeah", "Tampa"]
    prefs = [
        "Prefers a quiet environment and small groups.",
        "Needs close distance to family and frequent family visits.",
        "Enjoys gardening and music activities.",
        "Family wants best quality and reliable transportation.",
    ]

    dataset: List[Dict[str, Any]] = []
    for index in range(count):
        cog_value, cog_sentence = cognitive[index % len(cognitive)]
        mobility_value, mobility_sentence = mobility[(index // 2) % len(mobility)]
        medical_values, medical_sentence = medical[index % len(medical)]
        adl_values, adl_sentence = adl[index % len(adl)]
        language_values, language_sentence = languages[(index // 3) % len(languages)]

        item = {
            "relationship": relationships[index % len(relationships)],
            "age": ages[index % len(ages)],
            "cognitive_status": cog_value,
            "cognitive_sentence": cog_sentence,
            "mobility": mobility_value,
            "mobility_sentence": mobility_sentence,
            "medical_conditions": medical_values,
            "medical_sentence": medical_sentence,
            "adl": adl_values,
            "adl_sentence": adl_sentence,
            "languages": language_values,
            "language_sentence": language_sentence,
            "budget": budgets[index % len(budgets)],
            "budget_sentence": f"Our budget is ${budgets[index % len(budgets)]:,} per month.",
            "location": locations[index % len(locations)],
            "location_sentence": f"We are looking in {locations[index % len(locations)]}, Florida.",
            "preference_sentence": prefs[index % len(prefs)],
        }

        expected_missing: List[str] = []
        include_missing: List[str] = []
        if index % 5 == 0:
            include_missing.append("budget")
            expected_missing.append("budget")
        if index % 7 == 0:
            include_missing.append("location")
            expected_missing.append("location")
        if index % 9 == 0:
            include_missing.append("adl")
            expected_missing.append("adl")

        item["text"] = _render_case_template(item, include_missing)
        item["expected_missing"] = sorted(set(expected_missing))
        dataset.append(item)

    return dataset


def run_case_understanding_validation(db: Session, sample_size: int = 120) -> Dict[str, Any]:
    rows = _benchmark_dataset(max(100, sample_size))
    field_checks = ["age", "cognitive_status", "mobility", "budget", "location"]

    total_checks = 0
    correct_checks = 0
    missing_precision_scores: List[float] = []
    missing_recall_scores: List[float] = []
    followup_quality_scores: List[float] = []

    per_field_hits: Dict[str, int] = {key: 0 for key in field_checks}
    per_field_total: Dict[str, int] = {key: 0 for key in field_checks}

    for row in rows:
        parsed = parse_case_text(db, row["text"])
        structured = parsed.structured_profile

        extracted_age = structured.get("age", {}).get("value")
        expected_age = row["age"] if "budget" not in row["expected_missing"] or True else row["age"]
        if "age" not in row["expected_missing"]:
            per_field_total["age"] += 1
            total_checks += 1
            if extracted_age == expected_age:
                per_field_hits["age"] += 1
                correct_checks += 1

        if "cognitive_status" not in row["expected_missing"]:
            per_field_total["cognitive_status"] += 1
            total_checks += 1
            if structured.get("cognitive_status", {}).get("value") == row["cognitive_status"]:
                per_field_hits["cognitive_status"] += 1
                correct_checks += 1

        if "mobility" not in row["expected_missing"]:
            per_field_total["mobility"] += 1
            total_checks += 1
            if structured.get("mobility", {}).get("value") == row["mobility"]:
                per_field_hits["mobility"] += 1
                correct_checks += 1

        if "budget" not in row["expected_missing"]:
            per_field_total["budget"] += 1
            total_checks += 1
            if structured.get("budget", {}).get("value") == row["budget"]:
                per_field_hits["budget"] += 1
                correct_checks += 1

        if "location" not in row["expected_missing"]:
            per_field_total["location"] += 1
            total_checks += 1
            if str(structured.get("location", {}).get("value") or "").lower() == str(row["location"]).lower():
                per_field_hits["location"] += 1
                correct_checks += 1

        expected_missing = set(row["expected_missing"])
        predicted_missing = set(parsed.missing_critical_fields)
        true_positive = len(expected_missing.intersection(predicted_missing))
        precision = true_positive / max(1, len(predicted_missing))
        recall = true_positive / max(1, len(expected_missing)) if expected_missing else 1.0
        missing_precision_scores.append(precision)
        missing_recall_scores.append(recall)

        followups = parsed.follow_up_questions
        if expected_missing:
            covered = 0
            for field in expected_missing:
                keyword = field.replace("_", " ")
                if any(keyword in question.lower() for question in followups):
                    covered += 1
            followup_quality_scores.append(covered / len(expected_missing))
        else:
            followup_quality_scores.append(1.0 if len(followups) <= 3 else 0.8)

    extraction_accuracy = correct_checks / max(1, total_checks)

    return {
        "generated_at": _now().isoformat(),
        "sample_size": len(rows),
        "metrics": {
            "extraction_accuracy": round(extraction_accuracy, 4),
            "missing_field_precision": round(sum(missing_precision_scores) / max(1, len(missing_precision_scores)), 4),
            "missing_field_recall": round(sum(missing_recall_scores) / max(1, len(missing_recall_scores)), 4),
            "follow_up_question_quality": round(sum(followup_quality_scores) / max(1, len(followup_quality_scores)), 4),
        },
        "per_field_accuracy": {
            field: round(per_field_hits[field] / max(1, per_field_total[field]), 4)
            for field in field_checks
        },
        "quality_gate": {
            "minimum_cases": len(rows) >= 100,
            "extraction_accuracy_ge_0_8": extraction_accuracy >= 0.8,
            "follow_up_quality_ge_0_75": (sum(followup_quality_scores) / max(1, len(followup_quality_scores))) >= 0.75,
        },
    }
