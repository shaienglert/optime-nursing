from __future__ import annotations

import datetime as dt
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"
OUTPUT_JSON = REPO_ROOT / "database" / "community_intelligence_coverage.json"
OUTPUT_DOC = REPO_ROOT / "docs" / "COMMUNITY_INTELLIGENCE_COVERAGE.md"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

SOURCE_NAMES = [
    "CMS",
    "State License Registry",
    "State Inspections",
    "Deficiency Reports",
    "Fines",
    "License Actions",
    "Google Reviews",
    "Caring.com",
    "A Place For Mom",
    "SeniorAdvisor",
    "Yelp",
    "Seniorly",
    "Indeed",
    "Glassdoor",
    "Local News",
    "Press Releases",
    "Ownership Changes",
    "Lawsuits",
    "Court Records",
]


def _load_inventory() -> List[Dict[str, object]]:
    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    return list(payload.get("records") or [])


def _community_id(record: Dict[str, object]) -> str:
    source_url = str(record.get("source_url") or "")
    return source_url.removeprefix("https://www.seniorly.com/") or str(record.get("community_name") or "unknown")


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_seniorly_review_count(text: str) -> int:
    lowered = text.lower()
    if "there are currently no reviews here for this community" in lowered:
        return 0

    match = re.search(r"\b(\d+)\s+reviews?\b", text, re.I)
    if match:
        return int(match.group(1))

    return 0


def _parse_last_update(html: str) -> Optional[str]:
    timestamps = re.findall(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", html)
    if not timestamps:
        return None
    return max(timestamps)


def _fetch_seniorly_metrics(record: Dict[str, object]) -> Dict[str, object]:
    source_url = str(record.get("source_url") or "")
    if not source_url:
        return {"review_count": None, "last_update": None}

    response = requests.get(source_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    html = response.text
    text = _strip_html(html)
    return {
        "review_count": _parse_seniorly_review_count(text),
        "last_update": _parse_last_update(html),
    }


def _confidence_from_source_count(source_count: int) -> str:
    if source_count >= 8:
        return "HIGH"
    if 4 <= source_count <= 7:
        return "MEDIUM"
    if 1 <= source_count <= 3:
        return "LOW"
    return "UNKNOWN"


def _build_source_rows(record: Dict[str, object], seniorly_metrics: Dict[str, object]) -> List[Dict[str, object]]:
    community_name = str(record.get("community_name") or "")
    source_url = str(record.get("source_url") or "")
    license_profile_url = record.get("license_profile_url")
    state_license_number = record.get("state_license_number")

    available_source_count = 0
    source_rows: List[Dict[str, object]] = []

    for source_name in SOURCE_NAMES:
        if source_name == "Seniorly":
            source_available = True
            available_source_count += 1
            mention_count = seniorly_metrics.get("review_count")
            last_update = seniorly_metrics.get("last_update")
            source_row_url = source_url or None
            raw_refs = [source_url] if source_url else []
        elif source_name == "State License Registry" and license_profile_url:
            source_available = True
            available_source_count += 1
            mention_count = 1
            last_update = None
            source_row_url = str(license_profile_url)
            raw_refs = [str(license_profile_url)]
        else:
            source_available = False
            mention_count = None
            last_update = None
            source_row_url = None
            raw_refs = []

        source_rows.append(
            {
                "community_id": _community_id(record),
                "community_name": community_name,
                "county": record.get("county"),
                "state": "FL",
                "source_name": source_name,
                "source_available": source_available,
                "mention_count": mention_count,
                "last_update": last_update,
                "source_url": source_row_url,
                "confidence": _confidence_from_source_count(available_source_count),
                "raw_source_references": raw_refs,
            }
        )

    mention_count_total = sum(int(row["mention_count"]) for row in source_rows if isinstance(row["mention_count"], int))
    return [
        {
            "community_id": _community_id(record),
            "community_name": community_name,
            "county": record.get("county"),
            "state": "FL",
            "community_confidence": _confidence_from_source_count(available_source_count),
            "available_source_count": available_source_count,
            "mention_count_total": mention_count_total,
            "sources": source_rows,
        }
    ]


def _mean(values: Iterable[int]) -> Optional[float]:
    items = list(values)
    if not items:
        return None
    return round(sum(items) / len(items), 2)


def _build_summary(communities: List[Dict[str, object]]) -> Dict[str, object]:
    total_communities = len(communities)
    flattened_sources = [row for community in communities for row in community["sources"]]
    source_groups: Dict[str, List[Dict[str, object]]] = {}
    for row in flattened_sources:
        source_groups.setdefault(str(row["source_name"]), []).append(row)

    source_coverage: Dict[str, Dict[str, object]] = {}
    for source_name in SOURCE_NAMES:
        rows = source_groups.get(source_name, [])
        covered = sum(1 for row in rows if row["source_available"])
        source_coverage[source_name] = {
            "communities_covered": covered,
            "coverage_percentage": round((covered / total_communities) * 100, 2) if total_communities else 0.0,
            "average_mentions_per_community": round(
                sum(row["mention_count"] for row in rows if isinstance(row["mention_count"], int)) / total_communities,
                2,
            ) if total_communities else 0.0,
        }

    average_sources_per_community = round(
        sum(community["available_source_count"] for community in communities) / total_communities,
        2,
    ) if total_communities else 0.0
    average_mentions_per_community = round(
        sum(community["mention_count_total"] for community in communities) / total_communities,
        2,
    ) if total_communities else 0.0

    highest_coverage = sorted(
        communities,
        key=lambda item: (item["available_source_count"], item["mention_count_total"], str(item["community_name"] or "")),
        reverse=True,
    )[:10]
    lowest_coverage = sorted(
        communities,
        key=lambda item: (item["available_source_count"], item["mention_count_total"], str(item["community_name"] or "")),
    )[:10]

    confidence_distribution: Dict[str, int] = {}
    for community in communities:
        confidence_distribution[community["community_confidence"]] = confidence_distribution.get(community["community_confidence"], 0) + 1

    return {
        "source_coverage": source_coverage,
        "average_mentions_per_community": average_mentions_per_community,
        "average_sources_per_community": average_sources_per_community,
        "highest_information_coverage": [
            {
                "community_id": community["community_id"],
                "community_name": community["community_name"],
                "county": community["county"],
                "available_source_count": community["available_source_count"],
                "mention_count_total": community["mention_count_total"],
                "confidence": community["community_confidence"],
            }
            for community in highest_coverage
        ],
        "lowest_information_coverage": [
            {
                "community_id": community["community_id"],
                "community_name": community["community_name"],
                "county": community["county"],
                "available_source_count": community["available_source_count"],
                "mention_count_total": community["mention_count_total"],
                "confidence": community["community_confidence"],
            }
            for community in lowest_coverage
        ],
        "confidence_distribution": confidence_distribution,
    }


def _render_markdown(payload: Dict[str, object]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# Coverage Matrix")
    lines.append("")
    lines.append(f"Generated at UTC: {payload['generated_at_utc']}")
    lines.append(f"Communities analyzed: {payload['community_count']}")
    lines.append("")
    lines.append("## Source Coverage")
    lines.append("| Source | Communities Covered | Coverage | Avg Mentions / Community |")
    lines.append("|---|---:|---:|---:|")
    for source_name, stats in summary["source_coverage"].items():
        lines.append(
            f"| {source_name} | {stats['communities_covered']} | {stats['coverage_percentage']}% | {stats['average_mentions_per_community']} |"
        )
    lines.append("")
    lines.append(f"Average mentions per community: {summary['average_mentions_per_community']}")
    lines.append(f"Average number of sources per community: {summary['average_sources_per_community']}")
    lines.append("")
    lines.append("## Communities With Highest Information Coverage")
    lines.append("| Community | County | Available Sources | Mention Count Total | Confidence |")
    lines.append("|---|---|---:|---:|---|")
    for community in summary["highest_information_coverage"]:
        lines.append(
            f"| {community['community_name']} | {community['county']} | {community['available_source_count']} | {community['mention_count_total']} | {community['confidence']} |"
        )
    lines.append("")
    lines.append("## Communities With Lowest Information Coverage")
    lines.append("| Community | County | Available Sources | Mention Count Total | Confidence |")
    lines.append("|---|---|---:|---:|---|")
    for community in summary["lowest_information_coverage"]:
        lines.append(
            f"| {community['community_name']} | {community['county']} | {community['available_source_count']} | {community['mention_count_total']} | {community['confidence']} |"
        )
    lines.append("")
    lines.append("## Confidence Distribution")
    lines.append("| Confidence | Communities |")
    lines.append("|---|---:|")
    for level in ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        lines.append(f"| {level} | {summary['confidence_distribution'].get(level, 0)} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Source availability is based on verified public evidence only.")
    lines.append("- Missing values are null.")
    lines.append("- Raw source references are preserved in the JSON output.")
    return "\n".join(lines) + "\n"


def main() -> None:
    records = _load_inventory()
    seniorly_metrics: Dict[str, Dict[str, object]] = {}
    max_workers = min(24, max(4, len(records) // 16))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_seniorly_metrics, record): record for record in records}
        for future in as_completed(futures):
            record = futures[future]
            try:
                seniorly_metrics[_community_id(record)] = future.result()
            except Exception:
                seniorly_metrics[_community_id(record)] = {"review_count": None, "last_update": None}

    communities: List[Dict[str, object]] = []
    for record in records:
        communities.extend(_build_source_rows(record, seniorly_metrics.get(_community_id(record), {"review_count": None, "last_update": None})) )

    payload = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "community_count": len(communities),
        "source_names": SOURCE_NAMES,
        "confidence_rules": {
            "HIGH": "8+ independent sources",
            "MEDIUM": "4-7 independent sources",
            "LOW": "1-3 independent sources",
            "UNKNOWN": "No public sources found",
        },
        "communities": communities,
    }
    payload["summary"] = _build_summary(communities)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_DOC.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"json": str(OUTPUT_JSON), "doc": str(OUTPUT_DOC), "communities": len(communities)}, indent=2))


if __name__ == "__main__":
    main()