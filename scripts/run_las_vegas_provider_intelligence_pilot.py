#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.provider_organization_registry import (
    IMAGE_BRAND_ASSET,
    IMAGE_CORP_STOCK,
    IMAGE_FACILITY_SPECIFIC,
    IMAGE_ORG_SHARED,
    IMAGE_UNKNOWN,
    classify_shared_image,
    expected_displayable_coverage,
    match_location_candidate,
    utc_now_iso,
)
from scripts.pilot_facility_media_discovery import FacilitySeed, discover_media_for_facility, fetch_url
from scripts.run_statewide_facility_media_discovery import discover_with_retries
from app.services.facility_media_resolution import extract_candidate_images, classify_image_candidate

CANONICAL_PATH = REPO_ROOT / "database" / "nevada_facility_universe_canonical.json"
REGISTRY_PATH = REPO_ROOT / "database" / "provider_organization_registry.json"
BASELINE_PILOT_PATH = REPO_ROOT / "reports" / "MEDIA_LIVE_PILOT_100.json"
OUT_JSON = REPO_ROOT / "reports" / "LAS_VEGAS_PROVIDER_INTELLIGENCE_PILOT.json"
OUT_MD = REPO_ROOT / "reports" / "LAS_VEGAS_PROVIDER_INTELLIGENCE_PILOT.md"

DIRECTORY_HINT_PATHS = [
    "/locations/",
    "/communities/",
    "/find-a-community/",
    "/our-locations/",
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def _seed(row: Dict[str, Any]) -> FacilitySeed:
    return FacilitySeed(
        canonical_facility_id=str(row.get("canonical_id") or "").strip(),
        facility_name=str(row.get("facility_name") or "").strip(),
        city=str(row.get("city") or "").strip(),
        state=str(row.get("state") or "NV").strip() or "NV",
        address=str(row.get("address") or "").strip(),
        phone=str(row.get("phone") or "").strip(),
        cms_ccn=str((row.get("source_identity_ids") or {}).get("cms_ccn") or row.get("ccn") or "").strip(),
    )


def _fetch_safe(url: str) -> Optional[str]:
    try:
        status, _, body = fetch_url(url)
        if status >= 400:
            return None
        return body
    except Exception:
        return None


def _discover_directory(org_domain: str, facility: Dict[str, Any]) -> Dict[str, Any]:
    if not org_domain:
        return {
            "directory_url": "",
            "location_page_url": "",
            "location_match_evidence": {},
            "candidate_pages_checked": 0,
        }

    root = f"https://{org_domain}"
    best: Dict[str, Any] = {
        "directory_url": "",
        "location_page_url": "",
        "location_match_evidence": {},
        "candidate_pages_checked": 0,
    }

    for path in DIRECTORY_HINT_PATHS:
        directory_url = root.rstrip("/") + path
        body = _fetch_safe(directory_url)
        if body is None:
            continue

        best["directory_url"] = directory_url
        best["candidate_pages_checked"] += 1

        candidate = match_location_candidate(
            facility_name=str(facility.get("facility_name") or ""),
            city=str(facility.get("city") or ""),
            zip_code=str(facility.get("zip") or ""),
            phone=str(facility.get("phone") or ""),
            candidate_text=body,
            candidate_url=directory_url,
        )
        if candidate["matched"]:
            best["location_page_url"] = directory_url
            best["location_match_evidence"] = candidate
            return best

    homepage = _fetch_safe(root)
    if homepage:
        candidate = match_location_candidate(
            facility_name=str(facility.get("facility_name") or ""),
            city=str(facility.get("city") or ""),
            zip_code=str(facility.get("zip") or ""),
            phone=str(facility.get("phone") or ""),
            candidate_text=homepage,
            candidate_url=root,
        )
        best["candidate_pages_checked"] += 1
        if candidate["matched"]:
            best["location_page_url"] = root
            best["location_match_evidence"] = candidate

    return best


def _extract_org_first_media(location_page_url: str, facility_name: str) -> Dict[str, Any]:
    if not location_page_url:
        return {
            "org_first_candidates_found": 0,
            "org_first_facility_specific_candidates": 0,
            "org_first_rights_clear_candidates": 0,
            "org_first_terminal_result": "NO_LOCATION_PAGE",
            "org_first_sample_image_url": "",
        }

    body = _fetch_safe(location_page_url)
    if body is None:
        return {
            "org_first_candidates_found": 0,
            "org_first_facility_specific_candidates": 0,
            "org_first_rights_clear_candidates": 0,
            "org_first_terminal_result": "LOCATION_PAGE_UNREACHABLE",
            "org_first_sample_image_url": "",
        }

    images = extract_candidate_images(location_page_url, body)
    if not images:
        return {
            "org_first_candidates_found": 0,
            "org_first_facility_specific_candidates": 0,
            "org_first_rights_clear_candidates": 0,
            "org_first_terminal_result": "NO_IMAGE_CANDIDATE",
            "org_first_sample_image_url": "",
        }

    facility_specific = 0
    rights_clear = 0
    sample = ""
    for image in images:
        classified = classify_image_candidate(dict(image), facility_name=facility_name, official_page_url=location_page_url)
        status = str(classified.get("status") or "")
        reason = str(classified.get("reason") or "")
        shared_status = classify_shared_image(
            reuse_count=1,
            has_location_evidence=status == "VERIFIED",
            stock_like="STOCK" in reason,
            logo_like="LOGO" in reason,
        )
        if shared_status == IMAGE_FACILITY_SPECIFIC:
            facility_specific += 1
        elif shared_status in {IMAGE_ORG_SHARED, IMAGE_BRAND_ASSET, IMAGE_CORP_STOCK, IMAGE_UNKNOWN}:
            pass

        if status == "VERIFIED":
            rights_clear += 1
            if not sample:
                sample = str(image.get("url") or "")

    terminal = "FACILITY_SPECIFIC_IMAGE_CANDIDATE" if facility_specific > 0 else "NO_FACILITY_SPECIFIC_IMAGE"
    return {
        "org_first_candidates_found": len(images),
        "org_first_facility_specific_candidates": facility_specific,
        "org_first_rights_clear_candidates": rights_clear,
        "org_first_terminal_result": terminal,
        "org_first_sample_image_url": sample,
    }


def main() -> int:
    started = time.monotonic()
    canonical_payload = load_json(CANONICAL_PATH)
    registry_payload = load_json(REGISTRY_PATH)
    baseline_payload = load_json(BASELINE_PILOT_PATH)

    facilities = [
        row
        for row in (canonical_payload.get("records") or [])
        if isinstance(row, dict) and bool(row.get("is_las_vegas_valley"))
    ]

    relationships = registry_payload.get("facility_relationships") or []
    organizations = {
        str(row.get("organization_id") or ""): row
        for row in (registry_payload.get("records") or [])
        if isinstance(row, dict) and str(row.get("organization_id") or "").strip()
    }

    links_by_facility: Dict[str, List[Dict[str, Any]]] = {}
    for link in relationships:
        facility_id = str(link.get("canonical_facility_id") or "").strip()
        if not facility_id:
            continue
        links_by_facility.setdefault(facility_id, []).append(link)

    baseline_records = {
        str(row.get("canonical_facility_id") or "").strip(): row
        for row in (baseline_payload.get("records") or [])
        if isinstance(row, dict) and str(row.get("canonical_facility_id") or "").strip()
    }

    pilot_rows: List[Dict[str, Any]] = []
    resolved_exact_pages = 0
    newly_not_official_site_not_found = 0
    org_first_candidates_total = 0
    rights_clear_candidates_total = 0

    for facility in facilities:
        canonical_id = str(facility.get("canonical_id") or "").strip()
        if not canonical_id:
            continue

        links = links_by_facility.get(canonical_id, [])
        operator_link = next((link for link in links if str(link.get("relationship_type") or "") == "operator"), None)
        owner_link = next((link for link in links if str(link.get("relationship_type") or "") == "owner"), None)
        parent_link = next((link for link in links if str(link.get("relationship_type") or "") == "parent_company"), None)

        org_id = str((operator_link or owner_link or {}).get("organization_id") or "")
        org = organizations.get(org_id) or {}
        org_domain = str(org.get("official_domain") or "").strip()

        directory = _discover_directory(org_domain, facility)
        location_page = str(directory.get("location_page_url") or "")
        if location_page:
            resolved_exact_pages += 1

        org_first_media = _extract_org_first_media(location_page, str(facility.get("facility_name") or ""))
        org_first_candidates_total += int(org_first_media.get("org_first_candidates_found") or 0)
        rights_clear_candidates_total += int(org_first_media.get("org_first_rights_clear_candidates") or 0)

        fallback_result: Dict[str, Any] = {}
        if not location_page:
            # Organization-first failed; fallback to precise search discovery.
            seed = _seed(facility)
            fallback_result = discover_with_retries(seed, None, facility, max_candidates=8, max_retries=1)

        baseline = baseline_records.get(canonical_id) or {}
        baseline_official_missing = str(baseline.get("identity_status") or "") == "NOT_VERIFIED" or not str(baseline.get("official_website_url") or "").strip()
        current_official_found = bool(location_page or str(fallback_result.get("official_website_url") or "").strip() or org_domain)
        if baseline_official_missing and current_official_found:
            newly_not_official_site_not_found += 1

        terminal_result = str(org_first_media.get("org_first_terminal_result") or "")
        if not location_page and fallback_result:
            terminal_result = str(fallback_result.get("identity_status") or "NOT_VERIFIED")

        pilot_rows.append(
            {
                "canonical_facility_id": canonical_id,
                "facility_name": facility.get("facility_name") or "",
                "city": facility.get("city") or "",
                "state": facility.get("state") or "",
                "organization_found": bool(org_id),
                "independent": not bool(org_id),
                "operator": facility.get("operator_name") or "",
                "owner": facility.get("owner_name") or "",
                "parent_organization": (parent_link or {}).get("organization_id") or "",
                "organization_id": org_id,
                "official_organization_domain": org_domain,
                "exact_location_page": location_page,
                "identity_evidence": {
                    "operator_link": operator_link or {},
                    "owner_link": owner_link or {},
                    "domain_verification": org.get("domain_verification") or {},
                    "location_match": directory.get("location_match_evidence") or {},
                },
                "media_candidates_found_through_org_first_lookup": org_first_media.get("org_first_candidates_found") or 0,
                "rights_clear_image_candidates_through_org_first_lookup": org_first_media.get("org_first_rights_clear_candidates") or 0,
                "terminal_result": terminal_result,
                "fallback_identity_status": fallback_result.get("identity_status") if fallback_result else "",
            }
        )

    baseline_summary = baseline_payload.get("summary") or {}
    baseline_total = int(baseline_summary.get("facilities_processed") or len(facilities))
    baseline_verified_images = int(baseline_summary.get("images_accepted_facility_specific") or 0)

    projected_additional_verified = rights_clear_candidates_total
    coverage_projection = expected_displayable_coverage(
        baseline_verified_images=baseline_verified_images,
        total_facilities=baseline_total,
        projected_additional_verified=projected_additional_verified,
    )

    failure_distribution: Dict[str, int] = {}
    for row in pilot_rows:
        key = str(row.get("terminal_result") or "UNKNOWN")
        failure_distribution[key] = failure_distribution.get(key, 0) + 1

    output = {
        "generated_at_utc": utc_now_iso(),
        "pipeline": "provider-intelligence-organization-first-pilot",
        "scope": "las_vegas_42",
        "facilities_evaluated": len(facilities),
        "organizations_identified": int((registry_payload.get("metrics") or {}).get("organizations_identified") or 0),
        "independent_facilities_identified": int(registry_payload.get("independent_facility_count") or 0),
        "verified_organization_domains": int((registry_payload.get("metrics") or {}).get("verified_official_domains") or 0),
        "exact_location_pages_found": resolved_exact_pages,
        "newly_not_official_site_not_found": newly_not_official_site_not_found,
        "organization_first_media_candidates_found": org_first_candidates_total,
        "organization_first_rights_clear_candidates_found": rights_clear_candidates_total,
        "expected_displayable_image_coverage": coverage_projection,
        "baseline": {
            "facilities": baseline_total,
            "displayable_verified_images": baseline_verified_images,
            "dominant_failure": "official-site discovery",
        },
        "failure_distribution": failure_distribution,
        "records": pilot_rows,
        "wall_time_seconds": round(time.monotonic() - started, 3),
    }

    save_json(OUT_JSON, output)

    md: List[str] = []
    md.append("# Las Vegas Provider Intelligence Pilot")
    md.append("")
    md.append(f"Generated at: `{output['generated_at_utc']}`")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append(f"- Facilities evaluated: **{output['facilities_evaluated']}**")
    md.append(f"- Organizations identified: **{output['organizations_identified']}**")
    md.append(f"- Independent facilities identified: **{output['independent_facilities_identified']}**")
    md.append(f"- Verified organization domains: **{output['verified_organization_domains']}**")
    md.append(f"- Exact location pages found: **{output['exact_location_pages_found']}**")
    md.append(f"- Facilities no longer classified OFFICIAL_SITE_NOT_FOUND: **{output['newly_not_official_site_not_found']}**")
    md.append(f"- Organization-first media candidates found: **{output['organization_first_media_candidates_found']}**")
    md.append(f"- Organization-first rights-clear candidates found: **{output['organization_first_rights_clear_candidates_found']}**")
    md.append("")
    md.append("## Coverage Projection")
    md.append("")
    md.append(f"- Baseline displayable images: **{coverage_projection['baseline_verified_images']} / {output['baseline']['facilities']}**")
    md.append(f"- Projected displayable images after existing media gates: **{coverage_projection['projected_verified_images']} / {output['baseline']['facilities']}**")
    md.append(f"- Baseline coverage: **{coverage_projection['baseline_coverage_percent']}%**")
    md.append(f"- Projected coverage: **{coverage_projection['projected_coverage_percent']}%**")
    md.append("")
    md.append("## Failure Distribution")
    md.append("")
    md.append("| terminal_result | count |")
    md.append("| --- | ---: |")
    for key, value in sorted(failure_distribution.items(), key=lambda item: (-item[1], item[0])):
        md.append(f"| {key} | {value} |")

    md.append("")
    md.append("## Facility Records")
    md.append("")
    md.append("| canonical_facility_id | organization_found | independent | operator | owner | org_domain | exact_location_page | org_first_candidates | rights_clear_candidates | terminal_result |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |")
    for row in pilot_rows:
        md.append(
            "| {id} | {org_found} | {ind} | {op} | {owner} | {domain} | {page} | {cand} | {rights} | {term} |".format(
                id=row.get("canonical_facility_id") or "",
                org_found="YES" if row.get("organization_found") else "NO",
                ind="YES" if row.get("independent") else "NO",
                op=str(row.get("operator") or "").replace("|", "/"),
                owner=str(row.get("owner") or "").replace("|", "/"),
                domain=str(row.get("official_organization_domain") or ""),
                page=str(row.get("exact_location_page") or ""),
                cand=int(row.get("media_candidates_found_through_org_first_lookup") or 0),
                rights=int(row.get("rights_clear_image_candidates_through_org_first_lookup") or 0),
                term=str(row.get("terminal_result") or ""),
            )
        )

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    print("PILOT JSON:", OUT_JSON)
    print("PILOT MD:", OUT_MD)
    print("FACILITIES:", len(facilities))
    print("ORG-FIRST RIGHTS-CLEAR CANDIDATES:", rights_clear_candidates_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
