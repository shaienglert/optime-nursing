from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"
CMS_JSON = REPO_ROOT / "database" / "market_communities_south_florida.json"
OUTPUT_JSON = REPO_ROOT / "database" / "community_deep_intelligence_v3.json"

CMS_PROVIDER_DATASET_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"


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


def _community_id(inv: Dict[str, object]) -> str:
    return _slug(inv.get("source_url") or inv.get("community_name"))


def _source_row(name: str, url: Optional[str], reliability_score: Optional[int], last_updated: Optional[str], collected_at: str) -> Dict[str, object]:
    return {
        "source_name": name,
        "source_url": url,
        "reliability_score": reliability_score,
        "last_updated": last_updated,
        "collection_timestamp_utc": collected_at,
    }


def _source_rows(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> List[Dict[str, object]]:
    return [
        _source_row("Seniorly profile", _clean_text(inv.get("source_url")) or None, 3 if inv.get("source_url") else None, None, collected_at),
        _source_row("Official website", _clean_text(inv.get("website")) or None, 4 if inv.get("website") else None, None, collected_at),
        _source_row("State license profile", _clean_text(inv.get("license_profile_url")) or None, 5 if inv.get("license_profile_url") else None, None, collected_at),
        _source_row("CMS provider dataset", CMS_PROVIDER_DATASET_URL if cms else None, 5 if cms else None, cms.get("source_processing_date") if cms else None, collected_at),
    ]


def _score_from_percent(value: Optional[float]) -> Optional[int]:
    if value is None:
        return None
    return max(0, min(100, round(value)))


def _numeric_ratings(cms: Optional[Dict[str, object]]) -> List[int]:
    if not cms:
        return []
    ratings = [cms.get("overall_rating"), cms.get("staffing_rating"), cms.get("inspection_rating"), cms.get("quality_rating")]
    return [int(value) for value in ratings if isinstance(value, (int, float))]


def _verified_source_count(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> int:
    return sum(1 for row in _source_rows(inv, cms, "") if row.get("source_url"))


def _transition_readiness_score(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> Optional[int]:
    ratings = _numeric_ratings(cms)
    if not ratings:
        return None
    care_bonus = 8 if "Assisted Living" in (inv.get("community_types") or []) else 0
    if "Memory Care" in (inv.get("community_types") or []):
        care_bonus += 6
    return _score_from_percent((sum(ratings) / len(ratings)) * 18 + care_bonus)


def _friendship_potential_score(inv: Dict[str, object]) -> Optional[int]:
    beds_raw = _clean_text(inv.get("units_beds"))
    match = re.search(r"(\d+)", beds_raw)
    if not match:
        return None
    beds = int(match.group(1))
    if beds <= 20:
        return 62
    if beds <= 80:
        return 72
    return 68


def _family_trust_score(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> Optional[int]:
    verified_sources = _verified_source_count(inv, cms)
    ratings = _numeric_ratings(cms)
    if verified_sources == 0 and not ratings:
        return None
    rating_component = (sum(ratings) / len(ratings)) * 14 if ratings else 0
    source_component = verified_sources * 10
    return _score_from_percent(rating_component + source_component)


def _independence_support_score(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> Optional[int]:
    care_types = inv.get("community_types") or []
    if not care_types:
        return None
    score = 45
    if "Independent Living" in care_types:
        score += 22
    if "Assisted Living" in care_types:
        score += 16
    if cms and isinstance(cms.get("staffing_rating"), (int, float)):
        score += int(cms.get("staffing_rating")) * 3
    return _score_from_percent(score)


def _red_flag_level(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> str:
    if not cms:
        return "UNKNOWN"
    flags = 0
    for key in ["overall_rating", "staffing_rating", "inspection_rating"]:
        value = cms.get(key)
        if isinstance(value, (int, float)) and value <= 2:
            flags += 1
    if bool(cms.get("changed_ownership_last_12m")):
        flags += 1
    if flags >= 3:
        return "HIGH"
    if flags >= 1:
        return "MODERATE"
    return "LOW"


def _adjustment_probability_12m(inv: Dict[str, object], cms: Optional[Dict[str, object]]) -> Optional[int]:
    ratings = _numeric_ratings(cms)
    verified_sources = _verified_source_count(inv, cms)
    if len(ratings) < 2 or verified_sources < 2:
        return None

    rating_component = (sum(ratings) / len(ratings)) * 14
    source_component = verified_sources * 6
    ownership_penalty = 10 if cms and bool(cms.get("changed_ownership_last_12m")) else 0
    independence_component = 8 if "Independent Living" in (inv.get("community_types") or []) else 0
    probability = rating_component + source_component + independence_component - ownership_penalty
    return _score_from_percent(probability)


def _base_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    sources = [row for row in _source_rows(inv, cms, collected_at) if row.get("source_url")]
    return {
        "community_id": _community_id(inv),
        "community_name": inv.get("community_name"),
        "county": inv.get("county"),
        "state": "FL",
        "collection_timestamp_utc": collected_at,
        "sources": sources,
    }


def _build_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    base = _base_record(inv, cms, collected_at)
    care_types = inv.get("community_types") or []

    transition_intelligence = {
        "facts": {
            "move_in_transition_program": None,
            "clinical_transition_support": None,
            "care_levels_available": care_types,
            "regulatory_support_context": {
                "overall_rating": cms.get("overall_rating") if cms else None,
                "staffing_rating": cms.get("staffing_rating") if cms else None,
                "inspection_rating": cms.get("inspection_rating") if cms else None,
            },
        },
        "opinions": [],
        "derived_scores": {
            "transition_readiness_score": _transition_readiness_score(inv, cms),
        },
    }

    friendship_intelligence = {
        "facts": {
            "resident_similarity_signals": None,
            "friendship_group_signals": None,
            "community_size_beds": inv.get("units_beds"),
            "engagement_evidence": None,
        },
        "opinions": [],
        "derived_scores": {
            "friendship_potential_score": _friendship_potential_score(inv),
        },
    }

    family_trust_intelligence = {
        "facts": {
            "official_website_present": bool(inv.get("website")) if inv.get("website") is not None else None,
            "state_license_profile_present": bool(inv.get("license_profile_url")) if inv.get("license_profile_url") is not None else None,
            "cms_profile_present": cms is not None,
            "phone_present": bool(inv.get("phone")) if inv.get("phone") is not None else None,
        },
        "opinions": [],
        "derived_scores": {
            "family_trust_score": _family_trust_score(inv, cms),
        },
    }

    dining_intelligence = {
        "facts": {
            "food_quality_signals": None,
            "dining_flexibility": None,
            "dietary_accommodations": None,
            "kosher_meals": None,
            "meal_service_details": None,
        },
        "opinions": [],
        "derived_scores": {
            "dining_support_score": None,
        },
    }

    independence_intelligence = {
        "facts": {
            "independent_living_available": "Independent Living" in care_types if care_types else None,
            "assisted_living_available": "Assisted Living" in care_types if care_types else None,
            "memory_care_available": "Memory Care" in care_types if care_types else None,
            "transportation_services": None,
            "mobility_support_signals": None,
        },
        "opinions": [],
        "derived_scores": {
            "independence_support_score": _independence_support_score(inv, cms),
        },
    }

    visit_intelligence = {
        "facts": {
            "family_distance": None,
            "travel_time": None,
            "visit_flexibility_signals": None,
            "parking_access": None,
            "family_visit_support": None,
        },
        "opinions": [],
        "derived_scores": {
            "visit_support_score": None,
        },
    }

    red_flag_intelligence = {
        "verified_findings": {
            "low_overall_rating": bool(cms and isinstance(cms.get("overall_rating"), (int, float)) and int(cms.get("overall_rating")) <= 2),
            "low_staffing_rating": bool(cms and isinstance(cms.get("staffing_rating"), (int, float)) and int(cms.get("staffing_rating")) <= 2),
            "low_inspection_rating": bool(cms and isinstance(cms.get("inspection_rating"), (int, float)) and int(cms.get("inspection_rating")) <= 2),
            "ownership_change_last_12m": cms.get("changed_ownership_last_12m") if cms else None,
        },
        "historical_issues": [],
        "current_issues": [],
        "allegations": [],
        "derived_scores": {
            "red_flag_level": _red_flag_level(inv, cms),
        },
    }

    success_prediction = {
        "twelve_month_success_adjustment_probability": _adjustment_probability_12m(inv, cms),
        "probability_method": "baseline_proxy_v1",
        "probability_inputs": {
            "regulatory_ratings_used": _numeric_ratings(cms),
            "verified_source_count": _verified_source_count(inv, cms),
            "ownership_change_last_12m": cms.get("changed_ownership_last_12m") if cms else None,
            "care_types": care_types,
        },
    }

    return {
        **base,
        "transition_intelligence": transition_intelligence,
        "friendship_intelligence": friendship_intelligence,
        "family_trust_intelligence": family_trust_intelligence,
        "dining_intelligence": dining_intelligence,
        "independence_intelligence": independence_intelligence,
        "visit_intelligence": visit_intelligence,
        "red_flag_intelligence": red_flag_intelligence,
        "success_prediction": success_prediction,
    }


def main() -> None:
    collected_at = _now_utc()
    inventory_records = _load_records(INVENTORY_JSON)
    cms_records = _load_records(CMS_JSON)
    cms_index = _build_cms_index(cms_records)

    records: List[Dict[str, object]] = []
    probabilities: List[int] = []
    for inv in inventory_records:
        cms = cms_index.get((_slug(inv.get("community_name")), _norm(inv.get("county"))))
        record = _build_record(inv, cms, collected_at)
        records.append(record)
        probability = record["success_prediction"]["twelve_month_success_adjustment_probability"]
        if isinstance(probability, int):
            probabilities.append(probability)

    payload = {
        "generated_at_utc": collected_at,
        "record_count": len(records),
        "policy": {
            "no_invented_information": True,
            "missing_values_are_null": True,
            "store_source_urls": True,
            "store_timestamps": True,
            "separate_facts_from_opinions": True,
            "separate_historical_issues_from_current_issues": True,
            "separate_allegations_from_verified_findings": True,
        },
        "modeling_notes": {
            "success_metric": "Probability of successful adjustment after 12 months",
            "success_metric_field": "twelve_month_success_adjustment_probability",
            "current_probability_method": "baseline_proxy_v1",
            "probability_is_outcome_validated": False,
            "probability_is_null_when_inputs_are_insufficient": True,
        },
        "coverage_summary": {
            "average_verified_sources_per_community": round(sum(_verified_source_count(inv, cms_index.get((_slug(inv.get("community_name")), _norm(inv.get("county")))) ) for inv in inventory_records) / len(inventory_records), 2) if inventory_records else 0.0,
            "communities_with_probability": len(probabilities),
            "average_probability_when_available": round(sum(probabilities) / len(probabilities), 2) if probabilities else None,
        },
        "records": records,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_JSON), "record_count": len(records), "communities_with_probability": len(probabilities)}, indent=2))


if __name__ == "__main__":
    main()