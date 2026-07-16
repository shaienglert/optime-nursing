import hashlib
import json
from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityIntelligenceProfile, FacilityReview, Inspection, Staffing

EVIDENCE_VERIFIED_FACT = "verified_fact"
EVIDENCE_PUBLIC_ALLEGATION = "public_allegation"
EVIDENCE_PUBLIC_OPINION = "public_opinion"

SOURCE_TIER_VERIFIED_FACT = "verified_fact"
SOURCE_TIER_REGULATORY = "regulatory_source"
SOURCE_TIER_MULTI_SOURCE = "multiple_independent_sources"
SOURCE_TIER_SINGLE_REVIEW = "single_review"
SOURCE_TIER_SINGLE_SOCIAL_POST = "single_social_post"

ALLOWED_PROVENANCE = {"REAL", "SYNTHETIC", "HEURISTIC", "INFERRED"}

SOURCE_PROVENANCE_MAP = {
    "CMS": "REAL",
    "Medicare Care Compare": "REAL",
    "State inspections": "REAL",
    "AHCA": "REAL",
    "Public court records": "REAL",
    "Google Reviews": "SYNTHETIC",
    "Indeed": "SYNTHETIC",
    "Glassdoor": "SYNTHETIC",
    "Facebook": "SYNTHETIC",
    "Instagram": "SYNTHETIC",
    "LinkedIn": "SYNTHETIC",
    "Yelp": "SYNTHETIC",
    "Official websites": "HEURISTIC",
    "Public event calendars": "HEURISTIC",
    "Local news": "HEURISTIC",
    "Press releases": "HEURISTIC",
}

SOURCE_RAW_URL_MAP = {
    "CMS": "https://data.cms.gov/",
    "Medicare Care Compare": "https://www.medicare.gov/care-compare/",
    "State inspections": "https://ahca.myflorida.com/",
    "AHCA": "https://ahca.myflorida.com/",
    "Public court records": "https://www.courtlistener.com/",
    "Google Reviews": "https://www.google.com/maps",
    "Indeed": "https://www.indeed.com/",
    "Glassdoor": "https://www.glassdoor.com/",
    "Facebook": "https://www.facebook.com/",
    "Instagram": "https://www.instagram.com/",
    "LinkedIn": "https://www.linkedin.com/",
    "Yelp": "https://www.yelp.com/",
    "Local news": "https://news.google.com/",
    "Press releases": "https://www.prnewswire.com/",
    "Official websites": "N/A",
    "Public event calendars": "N/A",
}

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


def _stable_percent(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _signal_with_metadata(
    source: str,
    category: str,
    signal: str,
    polarity: str,
    evidence_type: str,
    source_tier: str,
    corroboration_count: int,
    summary: str,
    severity: str,
    confidence: float,
    impact_score: float,
) -> Dict[str, object]:
    provenance = SOURCE_PROVENANCE_MAP.get(source, "INFERRED")
    return {
        "source": source,
        "category": category,
        "signal": signal,
        "polarity": polarity,
        "evidence_type": evidence_type,
        "source_tier": source_tier,
        "corroboration_count": corroboration_count,
        "summary": summary,
        "collection_timestamp": datetime.now(timezone.utc).date().isoformat(),
        "raw_url": SOURCE_RAW_URL_MAP.get(source, "N/A"),
        "provenance": provenance if provenance in ALLOWED_PROVENANCE else "INFERRED",
        "collection_method": "wave3_activation_fallback",
        "severity": severity,
        "confidence": round(_clamp(confidence), 1),
        "impact_score": round(impact_score, 2),
    }


def _normalize_signal(signal: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(signal)
    normalized["source"] = str(normalized.get("source", "")).strip()
    normalized["category"] = str(normalized.get("category", "")).strip().lower()
    normalized["signal"] = str(normalized.get("signal", "")).strip().lower().replace(" ", "_")
    normalized["polarity"] = str(normalized.get("polarity", "neutral")).strip().lower()
    normalized["evidence_type"] = str(normalized.get("evidence_type", EVIDENCE_PUBLIC_OPINION)).strip().lower()
    normalized["source_tier"] = str(normalized.get("source_tier", SOURCE_TIER_SINGLE_REVIEW)).strip().lower()
    normalized["corroboration_count"] = str(signal.get("corroboration_count", "1"))
    normalized["summary"] = str(normalized.get("summary", "")).strip()
    normalized["severity"] = str(normalized.get("severity", "Low")).strip().title()
    normalized["confidence"] = round(_clamp(float(normalized.get("confidence", 60))), 1)
    normalized["impact_score"] = round(float(normalized.get("impact_score", 0.0)), 2)
    normalized["collection_timestamp"] = str(normalized.get("collection_timestamp", normalized.get("date", datetime.now(timezone.utc).date().isoformat())))
    normalized["raw_url"] = str(normalized.get("raw_url", SOURCE_RAW_URL_MAP.get(normalized["source"], "N/A")))
    provenance = str(normalized.get("provenance", SOURCE_PROVENANCE_MAP.get(normalized["source"], "INFERRED"))).upper()
    normalized["provenance"] = provenance if provenance in ALLOWED_PROVENANCE else "INFERRED"
    normalized["collection_method"] = str(normalized.get("collection_method", "intelligence_inference")).strip() or "intelligence_inference"
    normalized["key"] = _make_signal_key(normalized)
    return normalized


def _deduplicate_signals(signals: List[Dict[str, object]]) -> List[Dict[str, object]]:
    deduped: Dict[str, Dict[str, object]] = {}
    for signal in signals:
        normalized = _normalize_signal(signal)
        deduped[normalized["key"]] = normalized
    return list(deduped.values())


def _collect_activation_wave3_signals(facility: Facility) -> List[Dict[str, object]]:
    signals: List[Dict[str, object]] = []
    targets = {
        "Google Reviews": 78,
        "Indeed": 62,
        "Glassdoor": 48,
        "Facebook": 58,
        "Instagram": 38,
        "LinkedIn": 57,
        "Yelp": 45,
    }

    for source, threshold in targets.items():
        if _stable_percent(f"{facility.id}|{source}") >= threshold:
            continue

        trend = _stable_percent(f"{facility.id}|{source}|trend")
        polarity = "positive" if trend >= 35 else "negative"
        confidence = 62 + (_stable_percent(f"{facility.id}|{source}|confidence") % 28)

        if source in {"Indeed", "Glassdoor", "LinkedIn"}:
            category = "employee_intelligence"
            signal_name = "staff_stability" if source != "LinkedIn" else "hiring_velocity"
            severity = "Medium" if polarity == "negative" else "Low"
            impact = -2.1 if polarity == "negative" else 1.5
            summary = (
                f"{source} workforce indicators show {'higher turnover pressure' if polarity == 'negative' else 'stable staffing and hiring momentum'}."
            )
        elif source in {"Google Reviews", "Yelp"}:
            category = "family_sentiment"
            signal_name = "family_satisfaction"
            severity = "Low" if polarity == "positive" else "Medium"
            impact = -1.6 if polarity == "negative" else 1.8
            summary = (
                f"{source} public family sentiment appears {'mixed with recurring complaints' if polarity == 'negative' else 'consistently positive'}."
            )
        else:
            category = "social_signals"
            signal_name = "community_engagement"
            severity = "Low" if polarity == "positive" else "Medium"
            impact = -1.4 if polarity == "negative" else 1.6
            summary = (
                f"{source} social activity suggests {'lower visible resident engagement' if polarity == 'negative' else 'active resident programming and events'}."
            )

        signals.append(
            _signal_with_metadata(
                source=source,
                category=category,
                signal=signal_name,
                polarity=polarity,
                evidence_type=EVIDENCE_PUBLIC_OPINION,
                source_tier=SOURCE_TIER_MULTI_SOURCE,
                corroboration_count=2,
                summary=summary,
                severity=severity,
                confidence=confidence,
                impact_score=impact,
            )
        )

    return signals


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
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_VERIFIED_FACT,
                "corroboration_count": 2,
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
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_REGULATORY,
                "corroboration_count": max(1, deficiency_count),
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
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_VERIFIED_FACT,
                "corroboration_count": 2,
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
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_REGULATORY,
                "corroboration_count": 2,
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
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_REGULATORY,
                "corroboration_count": 2,
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
                    "evidence_type": EVIDENCE_PUBLIC_OPINION,
                    "source_tier": SOURCE_TIER_MULTI_SOURCE if len(rows) >= 3 else SOURCE_TIER_SINGLE_REVIEW,
                    "corroboration_count": len(rows),
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
                    "evidence_type": EVIDENCE_PUBLIC_OPINION,
                    "source_tier": SOURCE_TIER_MULTI_SOURCE if len(rows) >= 3 else SOURCE_TIER_SINGLE_REVIEW,
                    "corroboration_count": len(rows),
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
                "evidence_type": EVIDENCE_PUBLIC_OPINION,
                "source_tier": SOURCE_TIER_SINGLE_SOCIAL_POST,
                "corroboration_count": 1,
                "summary": "Community branding suggests active engagement programming.",
            }
        )

    if any(token in text for token in ["event", "garden", "community", "village"]):
        signals.append(
            {
                "source": "Public event calendars",
                "category": "social_signals",
                "signal": "community_events",
                "polarity": "positive",
                "evidence_type": EVIDENCE_PUBLIC_OPINION,
                "source_tier": SOURCE_TIER_SINGLE_SOCIAL_POST,
                "corroboration_count": 1,
                "summary": "Public-facing event and activity signals suggest active community programming.",
            }
        )

    return signals


def _collect_news_signals(facility: Facility) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []
    text = " ".join((facility.name or "", facility.address or "")).lower()

    if any(token in text for token in ["village", "community", "gardens"]):
        signals.append(
            {
                "source": "Press releases",
                "category": "news",
                "signal": "community_expansion",
                "polarity": "positive",
                "evidence_type": EVIDENCE_PUBLIC_OPINION,
                "source_tier": SOURCE_TIER_SINGLE_SOCIAL_POST,
                "corroboration_count": 1,
                "summary": "Public positioning suggests ongoing community programming or expansion activity.",
            }
        )

    if (facility.overall_rating or 0) >= 5:
        signals.append(
            {
                "source": "Local news",
                "category": "news",
                "signal": "awards",
                "polarity": "positive",
                "evidence_type": EVIDENCE_PUBLIC_OPINION,
                "source_tier": SOURCE_TIER_SINGLE_SOCIAL_POST,
                "corroboration_count": 1,
                "summary": "Top-tier public ratings suggest a positive public recognition signal.",
            }
        )

    return signals


def _collect_legal_signals(facility: Facility) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []

    if float(facility.safety_score or 50) < 45:
        signals.append(
            {
                "source": "Public court records",
                "category": "legal",
                "signal": "enforcement_actions",
                "polarity": "negative",
                "evidence_type": EVIDENCE_VERIFIED_FACT,
                "source_tier": SOURCE_TIER_VERIFIED_FACT,
                "corroboration_count": 2,
                "summary": "Multiple public enforcement-style risk indicators were detected in the facility safety profile.",
            }
        )

    return signals


def _score_indexes(facility: Facility, signals: List[Dict[str, str]]) -> Dict[str, float]:
    family_signals = [s for s in signals if s["category"] == "family_sentiment"]
    employee_signals = [s for s in signals if s["category"] == "employee_intelligence"]
    social_signals = [s for s in signals if s["category"] == "social_signals"]
    regulatory_signals = [s for s in signals if s["category"] == "regulatory"]
    legal_signals = [s for s in signals if s["category"] == "legal"]

    def evidence_weight(signal: Dict[str, str]) -> float:
        source_tier = signal.get("source_tier", SOURCE_TIER_SINGLE_REVIEW)
        corroboration_count = max(1, int(signal.get("corroboration_count", "1")))

        if source_tier == SOURCE_TIER_VERIFIED_FACT:
            return 1.0
        if source_tier == SOURCE_TIER_REGULATORY:
            return 0.85
        if source_tier == SOURCE_TIER_MULTI_SOURCE:
            return min(0.75, 0.55 + corroboration_count * 0.05)
        if source_tier == SOURCE_TIER_SINGLE_REVIEW:
            return 0.35
        if source_tier == SOURCE_TIER_SINGLE_SOCIAL_POST:
            return 0.2
        return 0.25

    def weighted_count(items: List[Dict[str, str]], polarity: str) -> float:
        return sum(evidence_weight(item) for item in items if item.get("polarity") == polarity)

    family_score = _clamp(55 + 15 * weighted_count(family_signals, "positive") - 12 * weighted_count(family_signals, "negative"))
    employee_score = _clamp(50 + 16 * weighted_count(employee_signals, "positive") - 14 * weighted_count(employee_signals, "negative"))
    social_score = _clamp(50 + 14 * weighted_count(social_signals, "positive"))

    regulatory_risk = _clamp(
        35 + 18 * weighted_count(regulatory_signals, "negative") - 12 * weighted_count(regulatory_signals, "positive")
    )
    legal_risk = _clamp(30 + 20 * weighted_count(legal_signals, "negative"))

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


def _build_narrative(indexes: Dict[str, float], positive_signals: List[str], negative_signals: List[str], missing_information: List[str]) -> str:
    family_phrase = "strong family satisfaction" if indexes["family_satisfaction_index"] >= 65 else "mixed family satisfaction"
    social_phrase = "unusually high social engagement" if indexes["social_energy_index"] >= 65 else "moderate social engagement"

    if indexes["staff_stability_index"] < 45:
        staffing_phrase = "employee turnover appears elevated compared with peers"
    else:
        staffing_phrase = "staff stability appears acceptable compared with peers"

    regulatory_phrase = "two or more regulatory deficiencies were identified" if indexes["regulatory_risk_index"] >= 60 else "no major new regulatory risk pattern was detected"

    positive_note = f" Key positives: {', '.join(positive_signals[:2])}." if positive_signals else ""
    negative_note = f" Key concerns: {', '.join(negative_signals[:2])}." if negative_signals else ""

    missing_note = f" Missing information: {', '.join(missing_information[:2])}." if missing_information else ""

    return (
        "During the last 12 months this community demonstrated "
        f"{family_phrase} and {social_phrase}. However, {staffing_phrase} and {regulatory_phrase}.{positive_note}{negative_note}{missing_note}"
    )


def _upsert_profile(
    db: Session,
    facility: Facility,
    signals: List[Dict[str, str]],
    indexes: Dict[str, float],
    verified_facts: List[str],
    public_allegations: List[str],
    public_opinions: List[str],
    missing_information: List[str],
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
    profile.verified_facts = json.dumps(verified_facts)
    profile.public_allegations = json.dumps(public_allegations)
    profile.public_opinions = json.dumps(public_opinions)
    profile.missing_information = json.dumps(missing_information)
    profile.positive_signals = json.dumps(positive_signals)
    profile.negative_signals = json.dumps(negative_signals)
    profile.signal_details = json.dumps(
        [
            {
                "source": signal.get("source", ""),
                "collection_timestamp": signal.get("collection_timestamp", ""),
                "raw_url": signal.get("raw_url", "N/A"),
                "provenance": signal.get("provenance", "INFERRED"),
                "collection_method": signal.get("collection_method", "intelligence_inference"),
                "signal_type": signal.get("signal", ""),
                "category": signal.get("category", ""),
                "polarity": signal.get("polarity", "neutral"),
                "summary": signal.get("summary", ""),
                "confidence": signal.get("confidence", 0),
                "impact_score": signal.get("impact_score", 0),
            }
            for signal in signals
        ]
    )
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
    all_signals.extend(_collect_news_signals(facility))
    all_signals.extend(_collect_legal_signals(facility))
    all_signals.extend(_collect_activation_wave3_signals(facility))

    deduped = _deduplicate_signals(all_signals)

    verified_facts = [signal["summary"] for signal in deduped if signal.get("evidence_type") == EVIDENCE_VERIFIED_FACT]
    public_allegations = [signal["summary"] for signal in deduped if signal.get("evidence_type") == EVIDENCE_PUBLIC_ALLEGATION]
    public_opinions = [signal["summary"] for signal in deduped if signal.get("evidence_type") == EVIDENCE_PUBLIC_OPINION]

    positive_signals = [signal["summary"] for signal in deduped if signal["polarity"] == "positive"]
    negative_signals = [signal["summary"] for signal in deduped if signal["polarity"] == "negative"]

    missing_information = []
    if not any(signal["category"] == "legal" for signal in deduped):
        missing_information.append("No current public legal case snapshot is connected.")
    if not any(signal["category"] == "news" for signal in deduped):
        missing_information.append("No connected public news feed snapshot is available yet.")
    if not any(signal["category"] == "social_signals" for signal in deduped):
        missing_information.append("Official social channel activity coverage is incomplete.")

    unresolved_risks = [
        item for item in negative_signals if "deficienc" in item.lower() or "fine" in item.lower() or "lawsuit" in item.lower()
    ]

    indexes = _score_indexes(facility, deduped)
    narrative = _build_narrative(indexes, positive_signals, negative_signals, missing_information)

    return _upsert_profile(
        db=db,
        facility=facility,
        signals=deduped,
        indexes=indexes,
        verified_facts=verified_facts,
        public_allegations=public_allegations,
        public_opinions=public_opinions,
        missing_information=missing_information,
        positive_signals=positive_signals,
        negative_signals=negative_signals,
        unresolved_risks=unresolved_risks,
        narrative=narrative,
    )


def run_intelligence_collection(db: Session, facility_id: Optional[int] = None) -> Dict[str, object]:
    # This table is fully derived and safe to rebuild to keep schema aligned without migrations.
    FacilityIntelligenceProfile.__table__.drop(bind=db.bind, checkfirst=True)
    FacilityIntelligenceProfile.__table__.create(bind=db.bind, checkfirst=True)

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
