from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

PIPELINE_VERSION = "provider-organization-registry-v1"

STRONG_SIGNAL_NPI = "EXACT_ORG_NPI"
STRONG_SIGNAL_CMS_OWNER_ID = "EXACT_CMS_OWNERSHIP_ID"
STRONG_SIGNAL_CORP_REG_ID = "EXACT_CORP_REGISTRATION_ID"
STRONG_SIGNAL_DOMAIN_NAME = "EXACT_OFFICIAL_DOMAIN_PLUS_LEGAL_NAME"
STRONG_SIGNAL_OWNERSHIP_LINK = "AUTHORITATIVE_OWNERSHIP_LINK"
STRONG_SIGNAL_LOCATION_DIRECTORY = "LOCATION_DIRECTORY_MATCH"

REL_OPERATOR = "operator"
REL_OWNER = "owner"
REL_PARENT = "parent_company"
REL_MANAGEMENT = "management_company"
REL_BRAND = "brand"

IMAGE_FACILITY_SPECIFIC = "FACILITY_SPECIFIC"
IMAGE_ORG_SHARED = "ORGANIZATION_SHARED"
IMAGE_BRAND_ASSET = "BRAND_ASSET"
IMAGE_CORP_STOCK = "CORPORATE_STOCK"
IMAGE_UNKNOWN = "UNKNOWN"

WEAK_TOKEN_STOPWORDS = {
    "care",
    "center",
    "centre",
    "facility",
    "health",
    "group",
    "company",
    "services",
    "management",
    "senior",
    "nursing",
    "rehabilitation",
    "llc",
    "inc",
    "ltd",
    "pllc",
    "lp",
    "co",
    "and",
    "the",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(value: Any) -> str:
    lowered = str(value or "").strip().lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def normalize_name(value: Any) -> str:
    text = normalize_text(value)
    return re.sub(r"\b(llc|inc|ltd|pllc|lp|corp|corporation|company|co)\b", "", text).strip()


def canonical_domain(url_or_domain: Any) -> str:
    text = str(url_or_domain or "").strip().lower()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    host = urlparse(text).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def weak_name_tokens(value: Any) -> List[str]:
    tokens = [t for t in normalize_name(value).split() if len(t) >= 3 and t not in WEAK_TOKEN_STOPWORDS]
    return sorted(set(tokens))


def _strong_keys(record: Mapping[str, Any]) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    npi = str(record.get("organization_npi") or "").strip()
    if npi:
        keys[STRONG_SIGNAL_NPI] = npi

    cms_owner_id = str(record.get("cms_ownership_identifier") or "").strip()
    if cms_owner_id:
        keys[STRONG_SIGNAL_CMS_OWNER_ID] = cms_owner_id

    state_reg = str(record.get("state_registration_identifier") or "").strip()
    if state_reg:
        keys[STRONG_SIGNAL_CORP_REG_ID] = state_reg

    domain = canonical_domain(record.get("official_domain") or record.get("official_corporate_website"))
    if domain:
        # Domain remains stable across common legal-name updates; keep IDs stable for rename events.
        keys[STRONG_SIGNAL_DOMAIN_NAME] = domain

    return keys


def build_organization_id(record: Mapping[str, Any]) -> str:
    strong = _strong_keys(record)
    if STRONG_SIGNAL_NPI in strong:
        seed = "npi|" + strong[STRONG_SIGNAL_NPI]
    elif STRONG_SIGNAL_CMS_OWNER_ID in strong:
        seed = "cms_owner|" + strong[STRONG_SIGNAL_CMS_OWNER_ID]
    elif STRONG_SIGNAL_CORP_REG_ID in strong:
        seed = "state_reg|" + strong[STRONG_SIGNAL_CORP_REG_ID]
    elif STRONG_SIGNAL_DOMAIN_NAME in strong:
        seed = "domain_name|" + strong[STRONG_SIGNAL_DOMAIN_NAME]
    else:
        # Stable fallback: legal name + state.
        seed = "fallback|" + normalize_name(record.get("legal_name")) + "|" + normalize_text(record.get("state"))
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16].upper()
    return f"ORG-{digest}"


def infer_org_type(name: str) -> str:
    normalized = normalize_text(name)
    if any(token in normalized for token in ("health", "rehab", "care", "nursing")):
        return "HEALTHCARE_OPERATOR"
    if any(token in normalized for token in ("holdings", "capital", "partners")):
        return "PARENT_HOLDING"
    return "ORGANIZATION"


def classify_shared_image(*, reuse_count: int, has_location_evidence: bool, stock_like: bool, logo_like: bool) -> str:
    if logo_like:
        return IMAGE_BRAND_ASSET
    if stock_like:
        return IMAGE_CORP_STOCK
    if reuse_count > 1 and not has_location_evidence:
        return IMAGE_ORG_SHARED
    if has_location_evidence:
        return IMAGE_FACILITY_SPECIFIC
    return IMAGE_UNKNOWN


def verify_domain_signals(
    *,
    legal_or_brand_name_on_site: bool,
    exact_corporate_address_or_phone: bool,
    official_corporate_registration_link: bool,
    facility_directory_match: bool,
    structured_org_data: bool,
    authoritative_ownership_link: bool,
) -> Tuple[bool, List[str]]:
    signals: List[str] = []
    if legal_or_brand_name_on_site:
        signals.append("LEGAL_OR_BRAND_NAME_ON_SITE")
    if exact_corporate_address_or_phone:
        signals.append("EXACT_CORPORATE_ADDRESS_OR_PHONE")
    if official_corporate_registration_link:
        signals.append("OFFICIAL_CORPORATE_REGISTRATION_LINK")
    if facility_directory_match:
        signals.append("FACILITY_LOCATION_DIRECTORY_MATCH")
    if structured_org_data:
        signals.append("STRUCTURED_ORGANIZATION_DATA")
    if authoritative_ownership_link:
        signals.append("AUTHORITATIVE_OWNERSHIP_RECORD_LINK")
    return len(signals) >= 2, signals


def _relationship(
    canonical_facility_id: str,
    organization_id: str,
    rel_type: str,
    evidence: Mapping[str, Any],
    confidence: str = "HIGH",
) -> Dict[str, Any]:
    return {
        "canonical_facility_id": canonical_facility_id,
        "organization_id": organization_id,
        "relationship_type": rel_type,
        "source_evidence": dict(evidence),
        "effective_date": evidence.get("effective_date") or "",
        "end_date": evidence.get("end_date") or "",
        "confidence": confidence,
        "conflict_status": "NONE",
    }


def _org_record_template(
    *,
    legal_name: str,
    state: str,
    official_domain: str,
    official_corporate_website: str,
    organization_type: str,
    source_evidence: Dict[str, Any],
) -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "organization_id": "",
        "legal_name": legal_name,
        "dba_brand_names": [],
        "former_names": [],
        "organization_type": organization_type,
        "parent_organization_id": None,
        "ownership_hierarchy": [],
        "operator_identifiers": {},
        "npi_identifiers": [],
        "cms_ownership_identifier": None,
        "state_registration_identifier": None,
        "official_domain": official_domain,
        "alternate_official_domains": [],
        "official_corporate_website": official_corporate_website,
        "official_locations_directory_url": "",
        "logo_source_url": "",
        "logo_rights_status": "UNKNOWN",
        "status": "ACTIVE",
        "aliases": [],
        "source_evidence": source_evidence,
        "retrieval_dates": {"first_seen": now, "last_seen": now},
        "identity_confidence": "HIGH",
        "conflict_status": "NONE",
        "pipeline_version": PIPELINE_VERSION,
        "state": state,
    }


def _merge_org(base: Dict[str, Any], incoming: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key in ("dba_brand_names", "former_names", "alternate_official_domains", "aliases", "npi_identifiers"):
        values = list(merged.get(key) or [])
        for item in incoming.get(key) or []:
            if item and item not in values:
                values.append(item)
        merged[key] = values

    for key in ("official_domain", "official_corporate_website", "official_locations_directory_url", "logo_source_url"):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming.get(key)

    if incoming.get("parent_organization_id") and not merged.get("parent_organization_id"):
        merged["parent_organization_id"] = incoming.get("parent_organization_id")

    source = dict(merged.get("source_evidence") or {})
    source.update(dict(incoming.get("source_evidence") or {}))
    merged["source_evidence"] = source

    now = utc_now_iso()
    retrieval_dates = dict(merged.get("retrieval_dates") or {})
    retrieval_dates.setdefault("first_seen", now)
    retrieval_dates["last_seen"] = now
    merged["retrieval_dates"] = retrieval_dates
    return merged


def build_provider_organization_registry(
    *,
    facilities: Sequence[Mapping[str, Any]],
    pilot_records: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    organizations: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    strong_index: Dict[str, str] = {}
    unresolved_duplicate_candidates: List[Dict[str, Any]] = []
    independent_facilities: List[str] = []

    for row in facilities:
        canonical_id = str(row.get("canonical_id") or "").strip()
        if not canonical_id:
            continue

        operator_name = str(row.get("operator_name") or "").strip()
        owner_name = str(row.get("owner_name") or "").strip()
        state = str(row.get("state") or "").strip() or "NV"
        pilot = pilot_records.get(canonical_id) or {}

        official_site = str(pilot.get("official_website_url") or "").strip()
        official_page = str(pilot.get("official_facility_page_url") or "").strip()
        official_domain = canonical_domain(official_site)

        if not operator_name and not owner_name:
            independent_facilities.append(canonical_id)
            continue

        role_candidates: List[Tuple[str, str]] = []
        if operator_name:
            role_candidates.append((REL_OPERATOR, operator_name))
        if owner_name:
            role_candidates.append((REL_OWNER, owner_name))

        for rel_type, org_name in role_candidates:
            record = _org_record_template(
                legal_name=org_name,
                state=state,
                official_domain=official_domain,
                official_corporate_website=("https://" + official_domain) if official_domain else "",
                organization_type=infer_org_type(org_name),
                source_evidence={
                    f"canonical:{canonical_id}:{rel_type}": {
                        "source": "canonical_universe",
                        "field": rel_type + "_name",
                        "value": org_name,
                        "source_retrieved_at": row.get("source_retrieved_at") or "",
                        "authoritative": True,
                    },
                    f"pilot:{canonical_id}": {
                        "source": "media_live_pilot",
                        "official_website_url": official_site,
                        "official_facility_page_url": official_page,
                        "identity_status": pilot.get("identity_status") or "",
                    },
                },
            )

            domain_verified, domain_signals = verify_domain_signals(
                legal_or_brand_name_on_site=bool(official_domain and normalize_name(org_name).replace(" ", "")[:6] in official_domain.replace("-", "")),
                exact_corporate_address_or_phone=False,
                official_corporate_registration_link=False,
                facility_directory_match=bool(official_page),
                structured_org_data=False,
                authoritative_ownership_link=True,
            )

            if domain_verified:
                record["identity_confidence"] = "HIGH"
            else:
                record["identity_confidence"] = "MEDIUM"
            record["domain_verification"] = {
                "verified": domain_verified,
                "signals": domain_signals,
                "verification_date": utc_now_iso(),
                "next_review_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
                "rejection_reason": "INSUFFICIENT_STRONG_SIGNALS" if not domain_verified else "",
            }

            organization_id = build_organization_id(record)
            record["organization_id"] = organization_id

            keys = _strong_keys(record)
            matched_org_id = ""
            for signal, value in keys.items():
                indexed = strong_index.get(f"{signal}:{value}")
                if indexed:
                    matched_org_id = indexed
                    break

            if matched_org_id and matched_org_id != organization_id:
                # Defensive unresolved collision path.
                unresolved_duplicate_candidates.append(
                    {
                        "left_organization_id": matched_org_id,
                        "right_organization_id": organization_id,
                        "reason": "STRONG_KEY_COLLISION",
                        "signals": keys,
                    }
                )

            existing = next((item for item in organizations if item["organization_id"] == organization_id), None)
            if existing is None:
                organizations.append(record)
            else:
                merged = _merge_org(existing, record)
                organizations = [merged if item["organization_id"] == organization_id else item for item in organizations]

            for signal, value in keys.items():
                strong_index[f"{signal}:{value}"] = organization_id

            links.append(
                _relationship(
                    canonical_facility_id=canonical_id,
                    organization_id=organization_id,
                    rel_type=rel_type,
                    evidence={
                        "source": "canonical_universe",
                        "operator_name": operator_name,
                        "owner_name": owner_name,
                        "official_domain": official_domain,
                    },
                    confidence="HIGH" if rel_type == REL_OWNER else "MEDIUM",
                )
            )

        if operator_name and owner_name and normalize_name(operator_name) != normalize_name(owner_name):
            op_org_id = build_organization_id({"legal_name": operator_name, "state": state, "official_domain": official_domain})
            owner_org_id = build_organization_id({"legal_name": owner_name, "state": state, "official_domain": official_domain})
            links.append(
                _relationship(
                    canonical_facility_id=canonical_id,
                    organization_id=owner_org_id,
                    rel_type=REL_PARENT,
                    evidence={
                        "source": "derived",
                        "note": "owner differs from operator; parent relation retained as unresolved unless explicit acquisition evidence exists",
                        "linked_operator_organization_id": op_org_id,
                    },
                    confidence="LOW",
                )
            )

    # Weak duplicate candidates are recorded, never auto-merged.
    by_state_name: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for org in organizations:
        key = (str(org.get("state") or "").upper(), normalize_name(org.get("legal_name")))
        by_state_name[key].append(org)
    for (_, normalized_name), orgs in by_state_name.items():
        if len(orgs) > 1 and normalized_name:
            unresolved_duplicate_candidates.append(
                {
                    "organization_ids": [item["organization_id"] for item in orgs],
                    "reason": "SAME_NORMALIZED_NAME_MULTIPLE_ORGS",
                    "normalized_name": normalized_name,
                }
            )

    organizations.sort(key=lambda item: (str(item.get("legal_name") or ""), str(item.get("organization_id") or "")))
    links.sort(key=lambda item: (item["canonical_facility_id"], item["relationship_type"], item["organization_id"]))

    by_org = Counter(link["organization_id"] for link in links if link["relationship_type"] in {REL_OPERATOR, REL_OWNER})
    top_orgs = [
        {
            "organization_id": org_id,
            "facility_count": count,
            "legal_name": next((org.get("legal_name") for org in organizations if org["organization_id"] == org_id), ""),
        }
        for org_id, count in by_org.most_common(20)
    ]

    domains_verified = sum(1 for org in organizations if bool((org.get("domain_verification") or {}).get("verified")))
    facilities_covered_by_verified_domains = len(
        {
            link["canonical_facility_id"]
            for link in links
            if bool(next((org for org in organizations if org["organization_id"] == link["organization_id"]), {}).get("domain_verification", {}).get("verified"))
        }
    )

    return {
        "generated_at_utc": utc_now_iso(),
        "pipeline_version": PIPELINE_VERSION,
        "status": "ACTIVE",
        "record_count": len(organizations),
        "records": organizations,
        "facility_relationship_count": len(links),
        "facility_relationships": links,
        "unresolved_duplicate_candidates": unresolved_duplicate_candidates,
        "independent_facility_count": len(independent_facilities),
        "independent_facilities": sorted(independent_facilities),
        "metrics": {
            "organizations_identified": len(organizations),
            "facility_to_operator_links": sum(1 for row in links if row["relationship_type"] == REL_OPERATOR),
            "facility_to_owner_links": sum(1 for row in links if row["relationship_type"] == REL_OWNER),
            "parent_company_links": sum(1 for row in links if row["relationship_type"] == REL_PARENT),
            "verified_official_domains": domains_verified,
            "facilities_covered_by_verified_domains": facilities_covered_by_verified_domains,
            "top_organizations_by_facility_count": top_orgs,
        },
    }


def match_location_candidate(
    *,
    facility_name: str,
    city: str,
    zip_code: str,
    phone: str,
    candidate_text: str,
    candidate_url: str,
) -> Dict[str, Any]:
    text = normalize_text(candidate_text)
    name_tokens = set(weak_name_tokens(facility_name))
    city_token = normalize_text(city)
    zip_token = re.sub(r"\D", "", str(zip_code or ""))[:5]
    phone_token = re.sub(r"\D", "", str(phone or ""))[-7:]
    url_norm = normalize_text(candidate_url)

    name_match = bool(name_tokens and all(token in text or token in url_norm for token in list(name_tokens)[:2]))
    city_match = bool(city_token and city_token in text)
    zip_match = bool(zip_token and zip_token in re.sub(r"\D", "", candidate_text))
    phone_match = bool(phone_token and phone_token in re.sub(r"\D", "", candidate_text))

    score = 0.0
    if name_match:
        score += 0.45
    if city_match:
        score += 0.2
    if zip_match:
        score += 0.2
    if phone_match:
        score += 0.15

    return {
        "candidate_url": candidate_url,
        "score": round(score, 3),
        "matched": score >= 0.65,
        "signals": {
            "name_match": name_match,
            "city_match": city_match,
            "zip_match": zip_match,
            "phone_match": phone_match,
        },
    }


def expected_displayable_coverage(*, baseline_verified_images: int, total_facilities: int, projected_additional_verified: int) -> Dict[str, Any]:
    baseline = baseline_verified_images
    projected = baseline_verified_images + max(0, projected_additional_verified)
    return {
        "baseline_verified_images": baseline,
        "projected_verified_images": projected,
        "baseline_coverage_percent": round((baseline / total_facilities * 100.0) if total_facilities else 0.0, 3),
        "projected_coverage_percent": round((projected / total_facilities * 100.0) if total_facilities else 0.0, 3),
    }
