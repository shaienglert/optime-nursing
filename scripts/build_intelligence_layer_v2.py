from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"
CMS_JSON = REPO_ROOT / "database" / "market_communities_south_florida.json"

OUTPUT_MANAGEMENT = REPO_ROOT / "database" / "community_management_intelligence.json"
OUTPUT_WORKFORCE = REPO_ROOT / "database" / "community_workforce_intelligence.json"
OUTPUT_CULTURAL = REPO_ROOT / "database" / "community_cultural_intelligence.json"
OUTPUT_SOCIAL = REPO_ROOT / "database" / "community_social_intelligence.json"
OUTPUT_TREND = REPO_ROOT / "database" / "community_trend_intelligence.json"
OUTPUT_OUTCOME = REPO_ROOT / "database" / "community_outcome_framework.json"

CMS_PROVIDER_DATASET_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"
CMS_CARE_COMPARE_URL = "https://www.medicare.gov/care-compare/"
AHCA_SEARCH_URL = "https://quality.healthfinder.fl.gov/Facility-Search/FacilityLocateSearch"


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean_text(value).lower())


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(value).lower()).strip()


def _load_records(path: Path) -> List[Dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("records") or [])


def _build_cms_index(cms_records: List[Dict[str, object]]) -> Dict[Tuple[str, str], Dict[str, object]]:
    index: Dict[Tuple[str, str], Dict[str, object]] = {}
    for record in cms_records:
        key = (_slug(record.get("community_name")), _norm(record.get("county")))
        if key[0]:
            index[key] = record
    return index


def _community_key(inv: Dict[str, object]) -> str:
    return _slug(inv.get("source_url") or inv.get("community_name"))


def _base_identity(inv: Dict[str, object], collected_at: str) -> Dict[str, object]:
    return {
        "community_id": _community_key(inv),
        "community_name": inv.get("community_name"),
        "county": inv.get("county"),
        "state": "FL",
        "collection_timestamp_utc": collected_at,
    }


def _source_row(source_name: str, source_url: Optional[str], reliability_score: Optional[int], last_updated: Optional[str], collected_at: str) -> Dict[str, object]:
    return {
        "source_name": source_name,
        "source_url": source_url,
        "reliability_score": reliability_score,
        "last_updated": last_updated,
        "collection_timestamp_utc": collected_at,
    }


def _score_from_percent(percent: Optional[float]) -> Optional[int]:
    if percent is None:
        return None
    return max(0, min(100, round(percent)))


def _derive_ownership_stability_score(cms: Optional[Dict[str, object]]) -> Optional[int]:
    if not cms or cms.get("changed_ownership_last_12m") is None:
        return None
    return 35 if bool(cms.get("changed_ownership_last_12m")) else 82


def _derive_management_stability_score(cms: Optional[Dict[str, object]]) -> Optional[int]:
    ownership_score = _derive_ownership_stability_score(cms)
    if ownership_score is None:
        return None
    return ownership_score


def _derive_leadership_turnover_risk(cms: Optional[Dict[str, object]]) -> Optional[str]:
    if not cms or cms.get("changed_ownership_last_12m") is None:
        return None
    return "ELEVATED" if bool(cms.get("changed_ownership_last_12m")) else "LOW"


def _derive_trend_direction(cms: Optional[Dict[str, object]]) -> Optional[str]:
    if not cms:
        return None
    if bool(cms.get("changed_ownership_last_12m")):
        return "DECLINING"
    ratings = [cms.get("overall_rating"), cms.get("staffing_rating"), cms.get("inspection_rating")]
    numeric_ratings = [int(value) for value in ratings if isinstance(value, (int, float))]
    if len(numeric_ratings) < 2:
        return "STABLE"
    average_rating = sum(numeric_ratings) / len(numeric_ratings)
    if average_rating >= 4.0:
        return "IMPROVING"
    if average_rating >= 3.0:
        return "STABLE"
    return "DECLINING"


def _derive_trend_score(cms: Optional[Dict[str, object]]) -> Optional[int]:
    if not cms:
        return None
    ratings = [cms.get("overall_rating"), cms.get("staffing_rating"), cms.get("inspection_rating"), cms.get("quality_rating")]
    numeric_ratings = [int(value) for value in ratings if isinstance(value, (int, float))]
    if not numeric_ratings:
        return None
    base = (sum(numeric_ratings) / len(numeric_ratings)) * 20
    if bool(cms.get("changed_ownership_last_12m")):
        base -= 15
    return _score_from_percent(base)


def _review_sources_count(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> int:
    count = 0
    if inv.get("source_url"):
        count += 1
    if inv.get("website"):
        count += 1
    if inv.get("license_profile_url"):
        count += 1
    if cms:
        count += 2
    return count


def _management_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("Official website", _clean_text(inv.get("website")) or None, 4 if inv.get("website") else None, None, collected_at),
        _source_row("State license profile", _clean_text(inv.get("license_profile_url")) or None, 5 if inv.get("license_profile_url") else None, None, collected_at),
        _source_row("CMS provider dataset", CMS_PROVIDER_DATASET_URL if cms else None, 5 if cms else None, cms.get("source_processing_date") if cms else None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "facts": {
            "executive_director_name": None,
            "executive_director_tenure_months": None,
            "director_of_nursing_name": None,
            "director_of_nursing_tenure_months": None,
            "administrator_changes": None,
            "ownership_changes": cms.get("changed_ownership_last_12m") if cms else None,
            "acquisition_history": None,
            "operator_changes": None,
            "operator_name": cms.get("operator_name") if cms else None,
            "legal_business_name": cms.get("legal_business_name") if cms else None,
            "ownership_type": cms.get("ownership_type") if cms else None,
        },
        "derived_scores": {
            "management_stability_score": _derive_management_stability_score(cms),
            "leadership_turnover_risk": _derive_leadership_turnover_risk(cms),
            "ownership_stability_score": _derive_ownership_stability_score(cms),
        },
        "opinions": [],
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
    }


def _workforce_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("CMS provider dataset", CMS_PROVIDER_DATASET_URL if cms else None, 5 if cms else None, cms.get("source_processing_date") if cms else None, collected_at),
        _source_row("Indeed", None, None, None, collected_at),
        _source_row("Glassdoor", None, None, None, collected_at),
        _source_row("Public job boards", None, None, None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "facts": {
            "open_rn_positions": None,
            "open_cna_positions": None,
            "open_caregiver_positions": None,
            "hiring_intensity": None,
            "employee_sentiment": None,
            "understaffing_signals": None,
            "burnout_signals": None,
            "training_quality_signals": None,
            "cms_staffing_rating": cms.get("staffing_rating") if cms else None,
        },
        "derived_scores": {
            "workforce_health_score": None,
            "staffing_risk_score": _score_from_percent((5 - int(cms.get("staffing_rating"))) * 20 if cms and isinstance(cms.get("staffing_rating"), (int, float)) else None),
            "burnout_risk_score": None,
        },
        "opinions": [],
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
    }


def _cultural_record(inv: Dict[str, object], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("Official website", _clean_text(inv.get("website")) or None, 4 if inv.get("website") else None, None, collected_at),
        _source_row("Seniorly profile", _clean_text(inv.get("source_url")) or None, 3 if inv.get("source_url") else None, None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "facts": {
            "languages_spoken": None,
            "hebrew_speaking_staff": None,
            "spanish_speaking_staff": None,
            "russian_speaking_staff": None,
            "religious_affiliation": None,
            "kosher_meals": None,
            "religious_services": None,
            "holiday_celebrations": None,
            "cultural_events": None,
        },
        "profiles": {
            "cultural_profile": None,
            "religious_profile": None,
            "language_profile": None,
        },
        "opinions": [],
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
    }


def _social_record(inv: Dict[str, object], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("Official website", _clean_text(inv.get("website")) or None, 4 if inv.get("website") else None, None, collected_at),
        _source_row("Seniorly profile", _clean_text(inv.get("source_url")) or None, 3 if inv.get("source_url") else None, None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "facts": {
            "activities_count": None,
            "activity_diversity": None,
            "resident_engagement_signals": None,
            "outdoor_spaces": None,
            "dining_flexibility": None,
            "transportation_services": None,
            "volunteer_programs": None,
            "community_size_beds": inv.get("units_beds"),
        },
        "derived_scores": {
            "social_life_score": None,
            "engagement_score": None,
            "independence_support_score": None,
        },
        "opinions": [],
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
    }


def _trend_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("Seniorly profile", _clean_text(inv.get("source_url")) or None, 3 if inv.get("source_url") else None, None, collected_at),
        _source_row("Official website", _clean_text(inv.get("website")) or None, 4 if inv.get("website") else None, None, collected_at),
        _source_row("State license profile", _clean_text(inv.get("license_profile_url")) or None, 5 if inv.get("license_profile_url") else None, None, collected_at),
        _source_row("CMS provider dataset", CMS_PROVIDER_DATASET_URL if cms else None, 5 if cms else None, cms.get("source_processing_date") if cms else None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "tracked_series": {
            "reviews": [],
            "staffing": [cms.get("staffing_rating")] if cms and cms.get("staffing_rating") is not None else [],
            "fines": [],
            "occupancy": [],
            "awards": [],
            "ownership_changes": [cms.get("changed_ownership_last_12m")] if cms and cms.get("changed_ownership_last_12m") is not None else [],
        },
        "derived_scores": {
            "trend_score": _derive_trend_score(cms),
            "trend_direction": _derive_trend_direction(cms),
        },
        "historical_issues": [],
        "current_issues": [],
        "opinions": [],
        "allegations": [],
    }


def _outcome_record(inv: Dict[str, object], collected_at: str) -> Dict[str, object]:
    identity = _base_identity(inv, collected_at)
    source_rows = [
        _source_row("Outcome tracking system", None, None, None, collected_at),
    ]
    return {
        **identity,
        "source_urls": [row for row in source_rows if row.get("source_url")],
        "framework": {
            "resident_profile": {
                "resident_id": None,
                "age": None,
                "gender": None,
                "mobility_level": None,
                "cognitive_status": None,
                "family_proximity": None,
                "family_involvement": None,
            },
            "chosen_community": {
                "community_id": _community_key(inv),
                "community_name": inv.get("community_name"),
            },
            "six_month_outcome": {
                "satisfaction": None,
                "relocation": None,
                "hospitalizations": None,
                "social_integration": None,
                "family_satisfaction": None,
            },
            "twelve_month_outcome": {
                "satisfaction": None,
                "relocation": None,
                "hospitalizations": None,
                "social_integration": None,
                "family_satisfaction": None,
            },
        },
        "derived_scores": {
            "outcome_success_probability": None,
        },
        "opinions": [],
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
    }


def _write_payload(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    collected_at = _now_utc()
    inventory_records = _load_records(INVENTORY_JSON)
    cms_records = _load_records(CMS_JSON)
    cms_index = _build_cms_index(cms_records)

    management_records: List[Dict[str, object]] = []
    workforce_records: List[Dict[str, object]] = []
    cultural_records: List[Dict[str, object]] = []
    social_records: List[Dict[str, object]] = []
    trend_records: List[Dict[str, object]] = []
    outcome_records: List[Dict[str, object]] = []

    verified_source_totals: List[int] = []
    for inv in inventory_records:
        cms = cms_index.get((_slug(inv.get("community_name")), _norm(inv.get("county"))))
        management_records.append(_management_record(inv, cms, collected_at))
        workforce_records.append(_workforce_record(inv, cms, collected_at))
        cultural_records.append(_cultural_record(inv, collected_at))
        social_records.append(_social_record(inv, collected_at))
        trend_records.append(_trend_record(inv, cms, collected_at))
        outcome_records.append(_outcome_record(inv, collected_at))
        verified_source_totals.append(_review_sources_count(inv, cms))

    average_verified_sources = round(sum(verified_source_totals) / len(verified_source_totals), 2) if verified_source_totals else 0.0
    common_meta = {
        "generated_at_utc": collected_at,
        "record_count": len(inventory_records),
        "policy": {
            "no_invented_information": True,
            "missing_values_are_null": True,
            "keep_timestamps": True,
            "keep_source_urls": True,
            "separate_facts_from_opinions": True,
            "separate_historical_issues_from_current_issues": True,
            "separate_allegations_from_verified_findings": True,
        },
        "coverage_summary": {
            "average_verified_sources_per_community": average_verified_sources,
            "success_kpi_target": 15,
            "success_kpi_met": average_verified_sources >= 15,
        },
    }

    _write_payload(OUTPUT_MANAGEMENT, {**common_meta, "layer": "management_intelligence", "records": management_records})
    _write_payload(OUTPUT_WORKFORCE, {**common_meta, "layer": "workforce_intelligence", "records": workforce_records})
    _write_payload(OUTPUT_CULTURAL, {**common_meta, "layer": "cultural_intelligence", "records": cultural_records})
    _write_payload(OUTPUT_SOCIAL, {**common_meta, "layer": "community_life_intelligence", "records": social_records})
    _write_payload(OUTPUT_TREND, {**common_meta, "layer": "trend_intelligence", "records": trend_records})
    _write_payload(OUTPUT_OUTCOME, {**common_meta, "layer": "outcome_intelligence_framework", "records": outcome_records})

    print(
        json.dumps(
            {
                "management": str(OUTPUT_MANAGEMENT),
                "workforce": str(OUTPUT_WORKFORCE),
                "cultural": str(OUTPUT_CULTURAL),
                "social": str(OUTPUT_SOCIAL),
                "trend": str(OUTPUT_TREND),
                "outcome": str(OUTPUT_OUTCOME),
                "record_count": len(inventory_records),
                "average_verified_sources_per_community": average_verified_sources,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()