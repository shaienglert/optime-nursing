from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from enrich_nevada_pca_operational_primary_sources import UNKNOWN
from enrich_nevada_pca_operational_primary_sources_v2 import (
    _allowed_candidate,
    bing_result_urls,
    duckduckgo_lite_urls,
    hcqc_external_links,
    verify_candidate,
)

GENERIC_BLOCKED = (
    "cms.gov", "medicare.gov", "dpbh.nv.gov", "nvdpbh.aithent.com", "health.nv.gov",
    "myhealthfacilitylicense.nv.gov", "aplaceformom.com", "caring.com", "seniorly.com",
    "yelp.com", "facebook.com", "instagram.com", "linkedin.com", "bbb.org", "yellowpages.com",
    "mapquest.com", "chamberofcommerce.com", "hcaoa.org", "npino.org", "npi-number-one.com",
    "npidb.org", "healthcare4ppl.com",
)


def _domain_blocked(url: str) -> bool:
    from urllib.parse import urlparse
    domain = urlparse(str(url or "")).netloc.lower().split(":", 1)[0]
    return not domain or any(domain == d or domain.endswith("." + d) for d in GENERIC_BLOCKED)


def _query_variants(task: dict[str, Any]) -> list[tuple[str, str]]:
    name = str(task.get("agency_name") or "").strip()
    city = str(task.get("city") or "").strip()
    phone = str(task.get("phone") or "").strip()
    address = str(task.get("address") or "").strip()
    license_number = str(task.get("license_number") or "").strip()
    license_root = license_number.split("-", 1)[0]
    variants: list[tuple[str, str]] = []
    if phone:
        variants.append((f'"{phone}" "{name}"', "BING_EXACT_PHONE"))
        variants.append((f'"{phone}" home care Nevada', "BING_EXACT_PHONE_GENERIC"))
    if address:
        variants.append((f'"{address}" "{name}"', "BING_EXACT_ADDRESS"))
    if license_root:
        variants.append((f'"{license_root}" "{name}" Nevada personal care', "BING_LICENSE_ROOT"))
    variants.append((f'"{name}" "{city}" Nevada home care', "BING_NAME_CITY"))
    return variants


def discover_candidates_v4(task: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for url, title in hcqc_external_links(task):
        if not _allowed_candidate(url) or _domain_blocked(url) or url in seen:
            continue
        seen.add(url)
        candidates.append({"url": url, "title": title, "discovery_method": "HCQC_EXTERNAL_LINK"})

    for query, method in _query_variants(task):
        for url, title in bing_result_urls(query):
            if not _allowed_candidate(url) or _domain_blocked(url) or url in seen:
                continue
            seen.add(url)
            candidates.append({"url": url, "title": title, "discovery_method": method})
            if len(candidates) >= 15:
                return candidates

    name = str(task.get("agency_name") or "").strip()
    city = str(task.get("city") or "").strip()
    for url, title in duckduckgo_lite_urls(f'"{name}" "{city}" Nevada home care'):
        if not _allowed_candidate(url) or _domain_blocked(url) or url in seen:
            continue
        seen.add(url)
        candidates.append({"url": url, "title": title, "discovery_method": "DUCKDUCKGO_NAME_CITY"})
        if len(candidates) >= 15:
            break
    return candidates


def research_task_v4(task: dict[str, Any], throttle: float) -> dict[str, Any]:
    base = {
        "agency_id": task.get("agency_id") or UNKNOWN,
        "agency_name": task.get("agency_name") or UNKNOWN,
        "license_number": task.get("license_number") or UNKNOWN,
        "license_status": task.get("license_status") or UNKNOWN,
        "address": task.get("address") or UNKNOWN,
        "city": task.get("city") or UNKNOWN,
        "state": task.get("state") or "NV",
        "zip": task.get("zip") or UNKNOWN,
        "phone": task.get("phone") or UNKNOWN,
        "hcqc_detail_url": task.get("hcqc_detail_url") or UNKNOWN,
        "identity_verified": False,
        "primary_source_url": UNKNOWN,
        "serves_las_vegas_valley": UNKNOWN,
        "source_pages": [],
    }
    candidates = discover_candidates_v4(task)
    base["candidate_count"] = len(candidates)
    base["candidate_discovery_methods"] = sorted({c["discovery_method"] for c in candidates})
    for candidate in candidates:
        verified = verify_candidate(candidate, task, throttle)
        if verified:
            base.update(verified)
            base["research_status"] = "PRIMARY_SOURCE_VERIFIED"
            base["policy"] = "Discovery may use exact phone/address/license searches, but promotion requires primary-source identity verification. Third-party directories/associations/NPI mirrors are excluded. Missing operational facts remain UNKNOWN."
            return base
    base["research_status"] = "SOURCE_NOT_FOUND" if not candidates else "CANDIDATES_NOT_IDENTITY_VERIFIED"
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH_V4.json")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--throttle", type=float, default=0.05)
    args = ap.parse_args()
    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    tasks = list(queue.get("tasks") or [])
    selected = tasks[max(0, args.offset): max(0, args.offset) + max(0, args.limit)]
    records = [research_task_v4(task, max(0.0, args.throttle)) for task in selected]
    payload = {
        "schema_version": "nevada-pca-operational-primary-research-v4.1.0",
        "queue_task_count": len(tasks),
        "attempted": len(selected),
        "identity_verified": sum(r.get("identity_verified") is True for r in records),
        "source_not_found": sum(r.get("research_status") == "SOURCE_NOT_FOUND" for r in records),
        "candidates_not_identity_verified": sum(r.get("research_status") == "CANDIDATES_NOT_IDENTITY_VERIFIED" for r in records),
        "records": records,
        "policy": "Staging evidence only. Exact phone/address/license discovery is allowed, but production promotion still requires strong agency/operator primary-source identity and live HCQC/ALiS license gating.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("attempted", "identity_verified", "source_not_found", "candidates_not_identity_verified")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
