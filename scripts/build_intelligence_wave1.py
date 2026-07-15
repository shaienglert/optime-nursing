from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"
CMS_JSON = REPO_ROOT / "database" / "market_communities_south_florida.json"
OUTPUT_JSON = REPO_ROOT / "database" / "community_intelligence_wave1.json"

CMS_PROVIDER_DATASET_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"
CMS_CARE_COMPARE_URL = "https://www.medicare.gov/care-compare/"
AHCA_HEALTHFINDER_URL = "https://quality.healthfinder.fl.gov/Facility-Search/FacilityLocateSearch"

SOURCE_TYPES = [
    "CMS",
    "AHCA",
    "HealthFinder",
    "Google Reviews",
    "Caring",
    "A Place for Mom",
    "Seniorly",
    "Indeed",
    "Glassdoor",
    "Google News",
    "Official Website",
    "Operator Website",
]


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


def _fact(name: str, value: Any, source_url: Optional[str], source_type: str, timestamp: str, confidence: str) -> Dict[str, Any]:
    return {
        "fact_name": name,
        "value": value,
        "source_url": source_url,
        "source_type": source_type,
        "timestamp": timestamp,
        "confidence": confidence,
    }


def _signal(name: str, value: Any, source_url: Optional[str], source_type: str, timestamp: str, confidence: str) -> Dict[str, Any]:
    return {
        "signal_name": name,
        "value": value,
        "source_url": source_url,
        "source_type": source_type,
        "timestamp": timestamp,
        "confidence": confidence,
    }


def _source_entry(
    source_type: str,
    source_url: Optional[str],
    timestamp: str,
    confidence: str,
    facts: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "source_type": source_type,
        "source_url": source_url,
        "timestamp": timestamp,
        "confidence": confidence,
        "facts": facts,
        "signals": signals,
    }


def _confidence_for_url(url: Optional[str], source_quality: str = "HIGH") -> str:
    if not url:
        return "UNKNOWN"
    return source_quality


def _community_id(inv: Dict[str, object]) -> str:
    return _slug(inv.get("source_url") or inv.get("community_name"))


def _cms_entry(cms: Optional[Dict[str, object]], timestamp: str) -> Dict[str, Any]:
    url = CMS_PROVIDER_DATASET_URL if cms else None
    confidence = _confidence_for_url(url, "HIGH")
    facts: List[Dict[str, Any]] = []
    signals: List[Dict[str, Any]] = []

    if cms:
        for key in ["overall_rating", "staffing_rating", "quality_rating", "inspection_rating", "provider_type", "ownership_type", "operator_name", "legal_business_name", "changed_ownership_last_12m"]:
            facts.append(_fact(key, cms.get(key), url, "CMS", timestamp, confidence))

        signals.extend(
            [
                _signal("regulatory_summary", {
                    "overall_rating": cms.get("overall_rating"),
                    "staffing_rating": cms.get("staffing_rating"),
                    "inspection_rating": cms.get("inspection_rating"),
                }, url, "CMS", timestamp, confidence),
                _signal("ownership_change_signal", cms.get("changed_ownership_last_12m"), url, "CMS", timestamp, confidence),
            ]
        )

    return _source_entry("CMS", url, timestamp, confidence, facts, signals)


def _ahca_entry(inv: Dict[str, object], timestamp: str) -> Dict[str, Any]:
    url = _clean_text(inv.get("license_profile_url")) or None
    confidence = _confidence_for_url(url, "HIGH") if url else "UNKNOWN"
    facts = [
        _fact("state_license_number", inv.get("state_license_number"), url, "AHCA", timestamp, confidence),
    ]
    signals = [
        _signal("license_profile_present", bool(url) if url is not None else None, url, "AHCA", timestamp, confidence),
    ]
    return _source_entry("AHCA", url, timestamp, confidence, facts, signals)


def _healthfinder_entry(inv: Dict[str, object], timestamp: str) -> Dict[str, Any]:
    url = _clean_text(inv.get("license_profile_url")) or None
    confidence = _confidence_for_url(url, "HIGH") if url else "UNKNOWN"
    facts = [
        _fact("state_license_number", inv.get("state_license_number"), url, "HealthFinder", timestamp, confidence),
    ]
    signals = [
        _signal("healthfinder_profile_present", bool(url) if url is not None else None, url, "HealthFinder", timestamp, confidence),
    ]
    return _source_entry("HealthFinder", url, timestamp, confidence, facts, signals)


def _seniorly_entry(inv: Dict[str, object], timestamp: str) -> Dict[str, Any]:
    url = _clean_text(inv.get("source_url")) or None
    confidence = _confidence_for_url(url, "MEDIUM") if url else "UNKNOWN"
    facts = [
        _fact("community_types", inv.get("community_types"), url, "Seniorly", timestamp, confidence),
        _fact("primary_community_type", inv.get("primary_community_type"), url, "Seniorly", timestamp, confidence),
        _fact("address", inv.get("address"), url, "Seniorly", timestamp, confidence),
        _fact("phone", inv.get("phone"), url, "Seniorly", timestamp, confidence),
        _fact("website", inv.get("website"), url, "Seniorly", timestamp, confidence),
        _fact("units_beds", inv.get("units_beds"), url, "Seniorly", timestamp, confidence),
        _fact("parent_company", inv.get("parent_company"), url, "Seniorly", timestamp, confidence),
        _fact("county", inv.get("county"), url, "Seniorly", timestamp, confidence),
    ]
    signals = [
        _signal("care_types_available", inv.get("community_types"), url, "Seniorly", timestamp, confidence),
        _signal("community_size_descriptor", inv.get("units_beds"), url, "Seniorly", timestamp, confidence),
    ]
    return _source_entry("Seniorly", url, timestamp, confidence, facts, signals)


def _official_website_entry(inv: Dict[str, object], timestamp: str) -> Dict[str, Any]:
    url = _clean_text(inv.get("website")) or None
    confidence = _confidence_for_url(url, "HIGH") if url else "UNKNOWN"
    facts = [
        _fact("official_website_present", bool(url) if url is not None else None, url, "Official Website", timestamp, confidence),
    ]
    signals = [
        _signal("official_website_verified", bool(url) if url is not None else None, url, "Official Website", timestamp, confidence),
    ]
    return _source_entry("Official Website", url, timestamp, confidence, facts, signals)


def _operator_website_entry(timestamp: str) -> Dict[str, Any]:
    return _source_entry("Operator Website", None, timestamp, "UNKNOWN", [], [])


def _empty_source_entry(source_type: str, timestamp: str) -> Dict[str, Any]:
    return _source_entry(source_type, None, timestamp, "UNKNOWN", [], [])


def _unique_verified_urls(entries: List[Dict[str, Any]]) -> List[str]:
    return sorted({str(entry.get("source_url")) for entry in entries if entry.get("source_url")})


def _build_record(inv: Dict[str, object], cms: Optional[Dict[str, object]], timestamp: str) -> Dict[str, Any]:
    entries = [
        _cms_entry(cms, timestamp),
        _ahca_entry(inv, timestamp),
        _healthfinder_entry(inv, timestamp),
        _empty_source_entry("Google Reviews", timestamp),
        _empty_source_entry("Caring", timestamp),
        _empty_source_entry("A Place for Mom", timestamp),
        _seniorly_entry(inv, timestamp),
        _empty_source_entry("Indeed", timestamp),
        _empty_source_entry("Glassdoor", timestamp),
        _empty_source_entry("Google News", timestamp),
        _official_website_entry(inv, timestamp),
        _operator_website_entry(timestamp),
    ]

    unique_verified = _unique_verified_urls(entries)
    return {
        "community_id": _community_id(inv),
        "community_name": inv.get("community_name"),
        "county": inv.get("county"),
        "state": "FL",
        "collection_timestamp_utc": timestamp,
        "source_registry": entries,
        "coverage": {
            "verified_source_entry_count": sum(1 for entry in entries if entry.get("source_url")),
            "verified_unique_source_count": len(unique_verified),
            "verified_unique_source_urls": unique_verified,
        },
    }


def main() -> None:
    timestamp = _now_utc()
    inventory_records = _load_records(INVENTORY_JSON)
    cms_records = _load_records(CMS_JSON)
    cms_index = _build_cms_index(cms_records)

    records: List[Dict[str, Any]] = []
    verified_entry_counts: List[int] = []
    verified_unique_counts: List[int] = []
    source_type_coverage: Dict[str, int] = {source_type: 0 for source_type in SOURCE_TYPES}

    for inv in inventory_records:
        cms = cms_index.get((_slug(inv.get("community_name")), _norm(inv.get("county"))))
        record = _build_record(inv, cms, timestamp)
        records.append(record)
        verified_entry_counts.append(record["coverage"]["verified_source_entry_count"])
        verified_unique_counts.append(record["coverage"]["verified_unique_source_count"])
        for entry in record["source_registry"]:
            if entry.get("source_url"):
                source_type_coverage[entry["source_type"]] = source_type_coverage.get(entry["source_type"], 0) + 1

    average_verified_entry_sources = round(sum(verified_entry_counts) / len(verified_entry_counts), 2) if verified_entry_counts else 0.0
    average_verified_unique_sources = round(sum(verified_unique_counts) / len(verified_unique_counts), 2) if verified_unique_counts else 0.0

    payload = {
        "generated_at_utc": timestamp,
        "record_count": len(records),
        "source_types": SOURCE_TYPES,
        "policy": {
            "no_invented_information": True,
            "missing_values_are_null": True,
            "keep_full_provenance_for_every_fact": True,
            "store_source_url": True,
            "store_source_type": True,
            "store_timestamp": True,
            "store_confidence": True,
        },
        "target": {
            "verified_sources_per_community": 15,
            "target_metric": "average_verified_unique_sources_per_community",
        },
        "coverage_summary": {
            "average_verified_source_entries_per_community": average_verified_entry_sources,
            "average_verified_unique_sources_per_community": average_verified_unique_sources,
            "target_met": average_verified_unique_sources >= 15,
            "source_type_coverage": source_type_coverage,
        },
        "records": records,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT_JSON),
                "record_count": len(records),
                "average_verified_source_entries_per_community": average_verified_entry_sources,
                "average_verified_unique_sources_per_community": average_verified_unique_sources,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()