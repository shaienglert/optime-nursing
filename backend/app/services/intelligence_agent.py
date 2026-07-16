import hashlib
import json
from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityIntelligenceProfile, FacilityReview, Inspection, Staffing

UPDATE_FREQUENCY = {
    "news": "daily",
    "social_media": "daily",
    "reviews": "daily",
    "employee_sources": "weekly",
    "legal_sources": "weekly",
    "regulatory_sources": "monthly",
}

PUBLIC_SOURCE_REGISTRY = {
    "regulatory": [
        "CMS",
        "Medicare Care Compare",
        "State inspections",
        "AHCA",
        "Deficiency reports",
        "Staffing reports",
    ],
    "legal": [
        "Public court records",
        "Lawsuits",
        "Settlements",
        "Regulatory actions",
        "Fines",
        "Enforcement actions",
    ],
    "family_sentiment": [
        "Google Reviews",
        "Caring",
        "A Place for Mom",
        "Seniorly",
        "Yelp",
        "Facebook Reviews",
    ],
    "employee_intelligence": ["Indeed", "Glassdoor", "LinkedIn", "Job postings"],
    "news": ["Local news", "Press releases", "Ownership changes", "Awards", "Expansions", "Closures"],
    "social_signals": [
        "Official Facebook pages",
        "Official Instagram accounts",
        "Official YouTube channels",
        "Official websites",
        "Public event calendars",
        "Public images and videos",
    ],
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _make_signal_key(signal: Dict[str, str]) -> str:
    payload = "|".join(
        [
            signal.get("source", ""),
            signal.get("category", ""),
            signal.get("signal", ""),
            signal.get("polarity", ""),
            signal.get("summary", ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_signal(signal: Dict[str, str]) -> Dict[str, str]:
    normalized = dict(signal)
    normalized["source"] = normalized.get("source", "").strip()
    normalized["category"] = normalized.get("category", "").strip().lower()
    normalized["signal"] = normalized.get("signal", "").strip().lower().replace(" ", "_")
    normalized["polarity"] = normalized.get("polarity", "neutral").strip().lower()
    normalized["summary"] = normalized.get("summary", "").strip()
    normalized["key"] = _make_signal_key(normalized)
    return normalized


def _deduplicate_signals(signals: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped: Dict[str, Dict[str, str]] = {}
    for signal in signals:
        normalized = _normalize_signal(signal)
        deduped[normalized["key"]] = normalized
    return list(deduped.values())


def _collect_regulatory_signals(db: Session, facility: Facility) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []

    inspections = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()
    staffing = (
        db.query(Staffing)
        .filter(Staffing.facility_id == facility.id)
        .order_by(Staffing.id.desc())
        .first()
    )

    severe_deficiencies = sum(row.severe_deficiency_count or 0 for row in inspections)
    deficiency_count = sum(row.deficiency_count or 0 for row in inspections)

    if severe_deficiencies >= 2:
        signals.append(
            {
                "source": "State inspections",
                "category": "regulatory",
                "signal": "deficiencies",
                "polarity": "negative",
                "summary": f"{severe_deficiencies} severe deficiencies were identified.",
            }
        )
    elif deficiency_count > 0:
        signals.append(
            {
                "source": "State inspections",
                "category": "regulatory",
                "signal": "deficiencies",
                "polarity": "neutral",
                "summary": f"{deficiency_count} total deficiencies were identified.",
            }
        )

    fine_total = sum(float(row.fine_amount or 0) for row in inspections)
    if fine_total > 0:
        signals.append(
            {
                "source": "AHCA",
                "category": "legal",
                "signal": "fines",
                "polarity": "negative",
                "summary": f"Publicly reported fines total ${fine_total:,.0f}.",
            }
        )

    if staffing and (staffing.staffing_rating or 0) >= 4:
        signals.append(
            {
                "source": "CMS",
                "category": "regulatory",
                "signal": "staffing_reports",
                "polarity": "positive",
                "summary": "Staffing rating is strong in recent reports.",
            }
        )

    if (facility.quality_rating or 0) >= 4:
        signals.append(
            {
                "source": "Medicare Care Compare",
                "category": "regulatory",
                "signal": "improved_ratings",
                "polarity": "positive",
                "summary": "Quality rating is currently in a high tier.",
            }
        )

    return signals


def _collect_review_signals(db: Session, facility: Facility) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []
    review_rows = db.query(FacilityReview).filter(FacilityReview.facility_id == facility.id).all()
    if not review_rows:
        return signals

    family_sources = {"google", "caring", "a place for mom", "seniorly", "yelp", "facebook"}
    employee_sources = {"indeed", "glassdoor", "linkedin"}

    by_source: Dict[str, List[FacilityReview]] = {}
    for row in review_rows:
        source = (row.source or "unknown").strip().lower()
        by_source.setdefault(source, []).append(row)

    for source, rows in by_source.items():
        avg_rating = mean([float(r.rating or 0) for r in rows])
        if source in family_sources:
            polarity = "positive" if avg_rating >= 4 else "negative" if avg_rating <= 2.5 else "neutral"
            signals.append(
                {
                    "source": source.title(),
                    "category": "family_sentiment",
                    "signal": "family_satisfaction",
                    "polarity": polarity,
                    "summary": f"Average family review rating is {avg_rating:.2f}/5 from {len(rows)} public reviews.",
                }
            )
        if source in employee_sources:
            polarity = "positive" if avg_rating >= 3.8 else "negative" if avg_rating <= 2.8 else "neutral"
            signals.append(
                {
                    "source": source.title(),
                    "category": "employee_intelligence",
                    "signal": "staff_stability",
                    "polarity": polarity,
                    "summary": f"Average employee sentiment rating is {avg_rating:.2f}/5 from {len(rows)} public reviews.",
                }
            )

    return signals


def _collect_social_signals(facility: Facility) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []
    text = " ".join((facility.name or "", facility.address or "")).lower()

    if any(token in text for token in ["community", "center", "village"]):
        signals.append(
            {
                "source": "Official websites",
                "category": "social_signals",
                "signal": "community_engagement",
                "polarity": "positive",
                "summary": "Community branding suggests active engagement programming.",
            }
        )

    return signals


def _score_indexes(facility: Facility, signals: List[Dict[str, str]]) -> Dict[str, float]:
    family_signals = [s for s in signals if s["category"] == "family_sentiment"]
    employee_signals = [s for s in signals if s["category"] == "employee_intelligence"]
    social_signals = [s for s in signals if s["category"] == "social_signals"]
    regulatory_signals = [s for s in signals if s["category"] == "regulatory"]
    legal_signals = [s for s in signals if s["category"] == "legal"]

    family_score = _clamp(55 + 15 * len([s for s in family_signals if s["polarity"] == "positive"]) - 12 * len([s for s in family_signals if s["polarity"] == "negative"]))
    employee_score = _clamp(50 + 16 * len([s for s in employee_signals if s["polarity"] == "positive"]) - 14 * len([s for s in employee_signals if s["polarity"] == "negative"]))
    social_score = _clamp(50 + 14 * len([s for s in social_signals if s["polarity"] == "positive"]))

    regulatory_risk = _clamp(
        35 + 18 * len([s for s in regulatory_signals if s["polarity"] == "negative"]) - 12 * len([s for s in regulatory_signals if s["polarity"] == "positive"])
    )
    legal_risk = _clamp(30 + 20 * len([s for s in legal_signals if s["polarity"] == "negative"]))

    clinical_score = _clamp(float(facility.medical_quality_score or 0))
    reputation_score = _clamp((family_score * 0.5) + (social_score * 0.25) + (clinical_score * 0.25) - (legal_risk * 0.15))

    social_energy_index = _clamp((social_score * 0.55) + (family_score * 0.45))
    family_satisfaction_index = _clamp(family_score)
    staff_stability_index = _clamp(employee_score * 0.8 + float(facility.staffing_score or 50) * 0.2)
    regulatory_risk_index = _clamp(regulatory_risk)
    litigation_risk_index = _clamp(legal_risk)
    cultural_match_signals = _clamp(45 + (5 if "community" in (facility.name or "").lower() else 0))
    activity_density_index = _clamp(40 + 12 * len([s for s in signals if "event" in s["signal"] or "community" in s["signal"]]))
    community_engagement_index = _clamp((social_score * 0.6) + (activity_density_index * 0.4))
    clinical_quality_index = _clamp(clinical_score)
    reputation_index = _clamp(reputation_score)

    confidence = _clamp(45 + min(35, len(signals) * 4) + (10 if clinical_score > 0 else 0))

    return {
        "clinical_score": clinical_score,
        "family_score": family_score,
        "employee_score": employee_score,
        "social_score": social_score,
        "reputation_score": reputation_score,
        "legal_risk_score": legal_risk,
        "regulatory_risk_score": regulatory_risk,
        "social_energy_index": social_energy_index,
        "family_satisfaction_index": family_satisfaction_index,
        "staff_stability_index": staff_stability_index,
        "regulatory_risk_index": regulatory_risk_index,
        "litigation_risk_index": litigation_risk_index,
        "cultural_match_signals": cultural_match_signals,
        "activity_density_index": activity_density_index,
        "community_engagement_index": community_engagement_index,
        "clinical_quality_index": clinical_quality_index,
        "reputation_index": reputation_index,
        "intelligence_confidence": confidence,
    }


def _build_narrative(indexes: Dict[str, float], positive_signals: List[str], negative_signals: List[str]) -> str:
    family_phrase = "strong family satisfaction" if indexes["family_satisfaction_index"] >= 65 else "mixed family satisfaction"
    social_phrase = "unusually high social engagement" if indexes["social_energy_index"] >= 65 else "moderate social engagement"

    if indexes["staff_stability_index"] < 45:
        staffing_phrase = "employee turnover appears elevated compared with peers"
    else:
        staffing_phrase = "staff stability appears acceptable compared with peers"

    regulatory_phrase = "two or more regulatory deficiencies were identified" if indexes["regulatory_risk_index"] >= 60 else "no major new regulatory risk pattern was detected"

    positive_note = f" Key positives: {', '.join(positive_signals[:2])}." if positive_signals else ""
    negative_note = f" Key concerns: {', '.join(negative_signals[:2])}." if negative_signals else ""

    return (
        "During the last 12 months this community demonstrated "
        f"{family_phrase} and {social_phrase}. However, {staffing_phrase} and {regulatory_phrase}.{positive_note}{negative_note}"
    )


def _upsert_profile(
    db: Session,
    facility: Facility,
    signals: List[Dict[str, str]],
    indexes: Dict[str, float],
    positive_signals: List[str],
    negative_signals: List[str],
    unresolved_risks: List[str],
    narrative: str,
) -> FacilityIntelligenceProfile:
    profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == facility.id).first()
    if not profile:
        profile = FacilityIntelligenceProfile(facility_id=facility.id)
        db.add(profile)

    profile.last_updated = datetime.now(timezone.utc)
    profile.sources_used = json.dumps(sorted({signal["source"] for signal in signals}))
    profile.clinical_score = indexes["clinical_score"]
    profile.family_score = indexes["family_score"]
    profile.employee_score = indexes["employee_score"]
    profile.social_score = indexes["social_score"]
    profile.reputation_score = indexes["reputation_score"]
    profile.legal_risk_score = indexes["legal_risk_score"]
    profile.regulatory_risk_score = indexes["regulatory_risk_score"]
    profile.social_energy_index = indexes["social_energy_index"]
    profile.family_satisfaction_index = indexes["family_satisfaction_index"]
    profile.staff_stability_index = indexes["staff_stability_index"]
    profile.regulatory_risk_index = indexes["regulatory_risk_index"]
    profile.litigation_risk_index = indexes["litigation_risk_index"]
    profile.cultural_match_signals = indexes["cultural_match_signals"]
    profile.activity_density_index = indexes["activity_density_index"]
    profile.community_engagement_index = indexes["community_engagement_index"]
    profile.clinical_quality_index = indexes["clinical_quality_index"]
    profile.reputation_index = indexes["reputation_index"]
    profile.intelligence_confidence = indexes["intelligence_confidence"]
    profile.positive_signals = json.dumps(positive_signals)
    profile.negative_signals = json.dumps(negative_signals)
    profile.unresolved_risks = json.dumps(unresolved_risks)
    profile.intelligence_summary = narrative
    profile.update_frequency = json.dumps(UPDATE_FREQUENCY)

    db.commit()
    db.refresh(profile)
    return profile


def build_facility_intelligence_profile(db: Session, facility: Facility) -> FacilityIntelligenceProfile:
    all_signals = []
    all_signals.extend(_collect_regulatory_signals(db, facility))
    all_signals.extend(_collect_review_signals(db, facility))
    all_signals.extend(_collect_social_signals(facility))

    deduped = _deduplicate_signals(all_signals)

    positive_signals = [signal["summary"] for signal in deduped if signal["polarity"] == "positive"]
    negative_signals = [signal["summary"] for signal in deduped if signal["polarity"] == "negative"]

    unresolved_risks = []
    if not any(signal["category"] == "legal" for signal in deduped):
        unresolved_risks.append("Legal intelligence feed has no current public case snapshots.")
    if not any(signal["category"] == "news" for signal in deduped):
        unresolved_risks.append("News intelligence feed has not been connected yet.")
    if not any(signal["category"] == "social_signals" for signal in deduped):
        unresolved_risks.append("Official social channel activity has limited public signal coverage.")

    indexes = _score_indexes(facility, deduped)
    narrative = _build_narrative(indexes, positive_signals, negative_signals)

    return _upsert_profile(
        db=db,
        facility=facility,
        signals=deduped,
        indexes=indexes,
        positive_signals=positive_signals,
        negative_signals=negative_signals,
        unresolved_risks=unresolved_risks,
        narrative=narrative,
    )


def run_intelligence_collection(db: Session, facility_id: int | None = None) -> Dict[str, object]:
    if facility_id is not None:
        facilities = db.query(Facility).filter(Facility.id == facility_id).all()
    else:
        facilities = db.query(Facility).order_by(Facility.id.asc()).all()

    profiles: List[FacilityIntelligenceProfile] = []
    for facility in facilities:
        profiles.append(build_facility_intelligence_profile(db, facility))

    return {
        "processed": len(profiles),
        "facility_ids": [profile.facility_id for profile in profiles],
        "update_frequency": UPDATE_FREQUENCY,
        "source_registry": PUBLIC_SOURCE_REGISTRY,
    }
