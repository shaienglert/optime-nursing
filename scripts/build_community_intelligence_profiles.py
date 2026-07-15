from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"
CMS_JSON = REPO_ROOT / "database" / "market_communities_south_florida.json"
OUTPUT_JSON = REPO_ROOT / "database" / "community_intelligence_profiles.json"

CMS_CARE_COMPARE_URL = "https://www.medicare.gov/care-compare/"
CMS_PROVIDER_DATASET_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"
AHCA_SEARCH_URL = "https://quality.healthfinder.fl.gov/Facility-Search/FacilityLocateSearch"

DEFAULT_UPDATE_FREQUENCIES = {
    "daily": "DAILY",
    "weekly": "WEEKLY",
    "monthly": "MONTHLY",
    "quarterly": "QUARTERLY",
    "event": "EVENT_DRIVEN",
}


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean_text(value).lower())


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(value).lower()).strip()


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


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


def _confidence_level(source_count: int) -> str:
    if source_count >= 8:
        return "HIGH"
    if source_count >= 4:
        return "MEDIUM"
    if source_count >= 1:
        return "LOW"
    return "UNKNOWN"


def _coverage_score(source_count: int, total_sources: int) -> Optional[float]:
    if total_sources <= 0:
        return None
    return round(source_count / total_sources, 4)


def _source_row(
    tier: int,
    source_name: str,
    source_url: Optional[str],
    update_frequency: str,
    last_updated: Optional[str],
    reliability_score: Optional[int],
    collected_at: str,
) -> Dict[str, object]:
    return {
        "tier": tier,
        "source_name": source_name,
        "source_url": source_url,
        "update_frequency": update_frequency,
        "last_updated": last_updated,
        "reliability_score": reliability_score,
        "collection_timestamp_utc": collected_at,
    }


def _build_tier_1_sources(
    inv: Dict[str, object],
    cms: Optional[Dict[str, object]],
    collected_at: str,
) -> List[Dict[str, object]]:
    cms_last_updated = cms.get("source_processing_date") if cms else None
    state_last_updated = None
    license_profile_url = _clean_text(inv.get("license_profile_url")) or None

    return [
        _source_row(1, "CMS Care Compare", CMS_CARE_COMPARE_URL if cms else None, DEFAULT_UPDATE_FREQUENCIES["monthly"], cms_last_updated, 5 if cms else None, collected_at),
        _source_row(1, "CMS Provider Database", CMS_PROVIDER_DATASET_URL if cms else None, DEFAULT_UPDATE_FREQUENCIES["monthly"], cms_last_updated, 5 if cms else None, collected_at),
        _source_row(1, "AHCA Florida", license_profile_url or AHCA_SEARCH_URL, DEFAULT_UPDATE_FREQUENCIES["daily"], state_last_updated, 5 if license_profile_url else 4, collected_at),
        _source_row(1, "State Licensing Databases", license_profile_url, DEFAULT_UPDATE_FREQUENCIES["daily"], state_last_updated, 5 if license_profile_url else None, collected_at),
        _source_row(1, "Inspection Reports", CMS_PROVIDER_DATASET_URL if cms else None, DEFAULT_UPDATE_FREQUENCIES["monthly"], cms_last_updated, 5 if cms else None, collected_at),
        _source_row(1, "Deficiency Reports", None, DEFAULT_UPDATE_FREQUENCIES["monthly"], None, None, collected_at),
        _source_row(1, "Fines", None, DEFAULT_UPDATE_FREQUENCIES["monthly"], None, None, collected_at),
        _source_row(1, "License Actions", license_profile_url, DEFAULT_UPDATE_FREQUENCIES["daily"], None, 5 if license_profile_url else None, collected_at),
        _source_row(1, "Ownership Changes", CMS_PROVIDER_DATASET_URL if cms else None, DEFAULT_UPDATE_FREQUENCIES["monthly"], cms_last_updated, 4 if cms else None, collected_at),
    ]


def _build_tier_2_sources(collected_at: str) -> List[Dict[str, object]]:
    return [
        _source_row(2, "Google Reviews", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(2, "Caring.com", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(2, "A Place for Mom", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(2, "Seniorly", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, 3, collected_at),
        _source_row(2, "SeniorAdvisor", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(2, "Yelp", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
    ]


def _build_tier_3_sources(collected_at: str) -> List[Dict[str, object]]:
    return [
        _source_row(3, "Indeed", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(3, "Glassdoor", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
    ]


def _build_tier_4_sources(inv: Dict[str, object], collected_at: str) -> List[Dict[str, object]]:
    website = _clean_text(inv.get("website")) or None
    parent_company_site = None
    return [
        _source_row(4, "Official Website", website, DEFAULT_UPDATE_FREQUENCIES["monthly"], None, 4 if website else None, collected_at),
        _source_row(4, "Parent Company Website", parent_company_site, DEFAULT_UPDATE_FREQUENCIES["monthly"], None, None, collected_at),
        _source_row(4, "News", None, DEFAULT_UPDATE_FREQUENCIES["daily"], None, None, collected_at),
        _source_row(4, "Press Releases", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(4, "Awards", None, DEFAULT_UPDATE_FREQUENCIES["event"], None, None, collected_at),
        _source_row(4, "Community Events", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(4, "Expansions", None, DEFAULT_UPDATE_FREQUENCIES["event"], None, None, collected_at),
        _source_row(4, "Renovations", None, DEFAULT_UPDATE_FREQUENCIES["event"], None, None, collected_at),
    ]


def _build_tier_5_sources(collected_at: str) -> List[Dict[str, object]]:
    return [
        _source_row(5, "Lawsuits", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(5, "Court Records", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
        _source_row(5, "Regulatory Enforcement Actions", None, DEFAULT_UPDATE_FREQUENCIES["weekly"], None, None, collected_at),
    ]


def _build_tier_1_confirmed_findings(cms: Optional[Dict[str, object]]) -> Dict[str, object]:
    if not cms:
        return {
            "cms_overall_rating": None,
            "cms_staffing_rating": None,
            "cms_quality_rating": None,
            "cms_inspection_rating": None,
            "ownership_type": None,
            "changed_ownership_last_12m": None,
            "provider_type": None,
        }

    return {
        "cms_overall_rating": cms.get("overall_rating"),
        "cms_staffing_rating": cms.get("staffing_rating"),
        "cms_quality_rating": cms.get("quality_rating"),
        "cms_inspection_rating": cms.get("inspection_rating"),
        "ownership_type": cms.get("ownership_type"),
        "changed_ownership_last_12m": cms.get("changed_ownership_last_12m"),
        "provider_type": cms.get("provider_type"),
    }


def _build_profile(inv: Dict[str, object], cms: Optional[Dict[str, object]], collected_at: str) -> Dict[str, object]:
    tier_1_sources = _build_tier_1_sources(inv, cms, collected_at)
    tier_2_sources = _build_tier_2_sources(collected_at)
    tier_3_sources = _build_tier_3_sources(collected_at)
    tier_4_sources = _build_tier_4_sources(inv, collected_at)
    tier_5_sources = _build_tier_5_sources(collected_at)

    all_sources = tier_1_sources + tier_2_sources + tier_3_sources + tier_4_sources + tier_5_sources
    sources_analyzed = [row for row in all_sources if row.get("source_url")]
    source_count = len(sources_analyzed)

    source_refs = inv.get("source_refs") or []
    mention_count = len(source_refs) if isinstance(source_refs, list) else None

    profile = {
        "community_id": _slug(inv.get("source_url") or inv.get("community_name")),
        "community_name": inv.get("community_name"),
        "county": inv.get("county"),
        "state": "FL",
        "collection_timestamp_utc": collected_at,
        "source_map": {
            "tier_1_regulatory_intelligence": tier_1_sources,
            "tier_2_family_experience_intelligence": {
                "sources": tier_2_sources,
                "minimum_independent_mentions_threshold": 5,
                "signals": [],
            },
            "tier_3_employee_intelligence": {
                "sources": tier_3_sources,
                "signals": [],
            },
            "tier_4_community_intelligence": {
                "sources": tier_4_sources,
                "signals": [],
            },
            "tier_5_risk_intelligence": {
                "sources": tier_5_sources,
                "minimum_independent_mentions_threshold": 5,
                "patterns": [],
            },
        },
        "community_intelligence_profile": {
            "sources_analyzed": sources_analyzed,
            "source_count": source_count,
            "mention_count": mention_count,
            "coverage_score": _coverage_score(source_count, len(all_sources)),
            "confidence_level": _confidence_level(source_count),
            "trend_direction": "UNKNOWN",
        },
        "facts": {
            "confirmed_findings": {
                "regulatory": _build_tier_1_confirmed_findings(cms),
            },
            "opinions": {
                "family_experience": [],
                "employee_experience": [],
            },
            "allegations": {
                "unconfirmed": [],
                "patterns": [],
            },
        },
    }
    return profile


def main() -> None:
    inventory_records = _load_records(INVENTORY_JSON)
    cms_records = _load_records(CMS_JSON)
    cms_index = _build_cms_index(cms_records)
    collected_at = _now_utc()

    profiles: List[Dict[str, object]] = []
    for inv in inventory_records:
        cms = cms_index.get((_slug(inv.get("community_name")), _norm(inv.get("county"))))
        profiles.append(_build_profile(inv, cms, collected_at))

    payload = {
        "generated_at_utc": collected_at,
        "record_count": len(profiles),
        "scope": {
            "state": "FL",
            "counties": sorted({str(row.get("county")) for row in inventory_records if row.get("county")}),
        },
        "policy": {
            "no_invented_information": True,
            "missing_values_are_null": True,
            "store_original_source_urls": True,
            "store_collection_timestamps": True,
            "separate_facts_from_opinions": True,
            "separate_allegations_from_confirmed_findings": True,
        },
        "profiles": profiles,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_JSON), "record_count": len(profiles)}, indent=2))


if __name__ == "__main__":
    main()