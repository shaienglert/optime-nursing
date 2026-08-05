from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

from app.services.facility_media_resolution import classify_search_result, domain_of, normalize_text, norm_phone_digits

PIPELINE_VERSION = "government-identity-media-v1"
ELIGIBLE_PRIMARY_CATEGORIES = {"exterior", "entrance", "lobby", "garden", "campus"}
DISPLAYABLE_RIGHTS = {"OFFICIAL_DISPLAY_ALLOWED", "OWNER_AUTHORIZED", "LICENSED_EXTERNAL"}
FINAL_IMAGE_STATES = {"VERIFIED", "PROVISIONAL", "AMBIGUOUS", "REJECTED", "MISSING"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _source_entry(source: str, retrieved_at: str, value: Any) -> Dict[str, str]:
    return {"source": source, "retrieved_at": retrieved_at, "value": _clean(value)}


def build_authoritative_identity(
    canonical: Mapping[str, Any],
    inventory: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    inventory = inventory or {}
    evidence = canonical.get("source_evidence") or {}
    nppes = evidence.get("nppes") or {}
    identity_ids = canonical.get("source_identity_ids") or {}
    canonical_retrieved = _clean(canonical.get("source_retrieved_at"))
    nppes_retrieved = _clean(nppes.get("source_retrieved_at"))
    inventory_retrieved = _clean(inventory.get("source_retrieved_at") or inventory.get("retrieved_at"))

    fields: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    def add(field: str, source: str, retrieved_at: str, value: Any) -> None:
        if _clean(value):
            fields[field].append(_source_entry(source, retrieved_at, value))

    add("legal_name", "CANONICAL", canonical_retrieved, canonical.get("facility_name"))
    add("dba", "NPPES", nppes_retrieved, nppes.get("doing_business_as"))
    add("dba", "INVENTORY", inventory_retrieved, inventory.get("dba") or inventory.get("trade_name"))
    for former_name in inventory.get("former_names") or []:
        add("former_names", "INVENTORY", inventory_retrieved, former_name)
    add("operator_name", "INVENTORY", inventory_retrieved, inventory.get("operator_name") or inventory.get("parent_company"))
    add("owner_name", "INVENTORY", inventory_retrieved, inventory.get("owner_name"))
    add("street_address", "CANONICAL", canonical_retrieved, canonical.get("address"))
    add("street_address", "NPPES", nppes_retrieved, nppes.get("address_1"))
    add("city", "CANONICAL", canonical_retrieved, canonical.get("city"))
    add("city", "NPPES", nppes_retrieved, nppes.get("city"))
    add("county", "CANONICAL", canonical_retrieved, canonical.get("county"))
    add("state", "CANONICAL", canonical_retrieved, canonical.get("state"))
    add("state", "NPPES", nppes_retrieved, nppes.get("state"))
    add("zip_code", "CANONICAL", canonical_retrieved, canonical.get("zip"))
    add("zip_code", "NPPES", nppes_retrieved, nppes.get("postal_code"))
    add("public_phone", "CANONICAL", canonical_retrieved, canonical.get("phone"))
    add("public_phone", "NPPES", nppes_retrieved, nppes.get("telephone_number"))
    add("license_number", "NPPES", nppes_retrieved, nppes.get("license"))
    add("cms_certification_number", "CMS", canonical_retrieved, identity_ids.get("cms_ccn"))
    add("npi", "NPPES", nppes_retrieved, identity_ids.get("npi") or nppes.get("npi"))
    add("state_facility_identifier", "INVENTORY", inventory_retrieved, inventory.get("state_facility_id"))
    add("facility_type", "CANONICAL", canonical_retrieved, canonical.get("facility_type_raw"))
    add("bed_count", "CANONICAL", canonical_retrieved, canonical.get("licensed_beds_capacity"))
    add("official_regulator_url", "INVENTORY", inventory_retrieved, inventory.get("official_regulator_url"))
    for alias in inventory.get("aliases") or []:
        add("known_aliases", "INVENTORY", inventory_retrieved, alias)

    conflicts: List[Dict[str, Any]] = []
    for field, entries in fields.items():
        normalized_values = {normalize_text(item["value"]) for item in entries if item["value"]}
        if field in {"zip_code", "public_phone"}:
            normalized_values = {re.sub(r"\D", "", item["value"])[:10] for item in entries if item["value"]}
        if len(normalized_values) > 1:
            conflicts.append({"field": field, "values": entries})

    def preferred(field: str) -> str:
        entries = fields.get(field) or []
        return entries[0]["value"] if entries else ""

    return {
        "canonical_facility_id": _clean(canonical.get("canonical_id")),
        "facility_profile_id": _clean(canonical.get("facility_profile_id")),
        "legal_name": preferred("legal_name"),
        "dba": preferred("dba"),
        "former_names": [item["value"] for item in fields.get("former_names", [])],
        "operator_name": preferred("operator_name"),
        "owner_name": preferred("owner_name"),
        "street_address": preferred("street_address"),
        "city": preferred("city"),
        "county": preferred("county"),
        "state": preferred("state"),
        "zip_code": preferred("zip_code")[:5],
        "public_phone": preferred("public_phone"),
        "license_number": preferred("license_number"),
        "cms_certification_number": preferred("cms_certification_number"),
        "npi": preferred("npi"),
        "state_facility_identifier": preferred("state_facility_identifier"),
        "facility_type": preferred("facility_type"),
        "bed_count": preferred("bed_count"),
        "official_regulator_url": preferred("official_regulator_url"),
        "known_aliases": [item["value"] for item in fields.get("known_aliases", [])],
        "authoritative_identity_sources": dict(fields),
        "identity_conflicts": conflicts,
        "government_identity_confidence": 1.0 if preferred("legal_name") and preferred("street_address") else 0.6,
    }


def generate_search_queries(identity: Mapping[str, Any]) -> List[str]:
    name = _clean(identity.get("legal_name"))
    dba = _clean(identity.get("dba"))
    address = _clean(identity.get("street_address"))
    phone = _clean(identity.get("public_phone"))
    city = _clean(identity.get("city"))
    state = _clean(identity.get("state"))
    zip_code = _clean(identity.get("zip_code"))
    operator = _clean(identity.get("operator_name"))
    license_number = _clean(identity.get("license_number"))
    cms_number = _clean(identity.get("cms_certification_number"))
    candidates = [
        f'"{name}" "{address}"' if name and address else "",
        f'"{dba}" "{phone}"' if dba and phone else "",
        f'"{name}" "{city}" "{state}"' if name and city and state else "",
        f'"{operator}" "{name}"' if operator and name else "",
        f'"{license_number}" "Facility"' if license_number else "",
        f'"{cms_number}" "Official Website"' if cms_number else "",
        f'"{name}" "{zip_code}"' if name and zip_code else "",
        f'"{name}" "Contact"' if name else "",
    ]
    return list(dict.fromkeys(query for query in candidates if query))


def _contains_name(page_text: str, value: str) -> bool:
    normalized_value = normalize_text(value)
    return bool(normalized_value and normalized_value in normalize_text(page_text))


def verify_official_candidate(
    identity: Mapping[str, Any],
    *,
    candidate_url: str,
    page_text: str,
    source_classification: Optional[str] = None,
    is_operator_homepage: bool = False,
    regulator_linked: bool = False,
    search_rank: Optional[int] = None,
) -> Dict[str, Any]:
    classification = source_classification or classify_search_result(candidate_url, page_text)
    normalized_page = normalize_text(page_text)
    page_digits = re.sub(r"\D", "", page_text)
    matches: List[str] = []
    conflicts: List[str] = []

    names = [_clean(identity.get("legal_name")), _clean(identity.get("dba")), *[_clean(item) for item in identity.get("known_aliases") or []]]
    if any(_contains_name(page_text, name) for name in names if name):
        matches.append("exact_facility_name")
    address = _clean(identity.get("street_address"))
    if address and normalize_text(address) in normalized_page:
        matches.append("exact_street_address")
    phone = norm_phone_digits(_clean(identity.get("public_phone")))
    if len(phone) >= 7 and phone[-7:] in page_digits:
        matches.append("exact_public_phone")
    zip_code = re.sub(r"\D", "", _clean(identity.get("zip_code")))[:5]
    if zip_code and zip_code in page_digits:
        matches.append("exact_zip_code")
    operator = _clean(identity.get("operator_name"))
    if operator and _contains_name(page_text, operator) and _clean(identity.get("city")) and _contains_name(page_text, _clean(identity.get("city"))):
        matches.append("exact_operator_location")
    license_number = re.sub(r"\W", "", _clean(identity.get("license_number"))).lower()
    if license_number and license_number in re.sub(r"\W", "", page_text).lower():
        matches.append("license_reference")
    cms_number = re.sub(r"\D", "", _clean(identity.get("cms_certification_number")))
    if cms_number and cms_number in page_digits:
        matches.append("certification_reference")
    if regulator_linked:
        matches.append("regulator_provided_link")
    if '"@type"' in page_text and any(marker in page_text for marker in ("LocalBusiness", "MedicalBusiness", "NursingHome")):
        matches.append("facility_specific_json_ld")

    found_phones = set()
    for phone_match in re.findall(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", page_text):
        normalized_phone = norm_phone_digits(phone_match)
        if normalized_phone:
            found_phones.add(normalized_phone)
    if phone and found_phones and not any(item.endswith(phone[-10:]) or item.endswith(phone[-7:]) for item in found_phones):
        conflicts.append("public_phone")

    location_matches = {"exact_street_address", "exact_public_phone", "exact_zip_code", "exact_operator_location", "facility_specific_json_ld", "regulator_provided_link"}
    exact_location_verified = len(set(matches)) >= 2 and bool(location_matches.intersection(matches))
    official_source = classification in {"POSSIBLE_OFFICIAL_PAGE", "POSSIBLE_OFFICIAL_FACILITY_PAGE", "POSSIBLE_OFFICIAL_OPERATOR_PAGE"}
    verified = official_source and exact_location_verified and not conflicts and not is_operator_homepage
    status = "VERIFIED" if verified else "OFFICIAL_OPERATOR_FOUND_LOCATION_UNVERIFIED" if official_source and is_operator_homepage else "AMBIGUOUS" if matches else "REJECTED"
    rejection_reason = "" if verified else "OPERATOR_HOMEPAGE_NOT_LOCATION_PAGE" if is_operator_homepage else "NON_OFFICIAL_SOURCE_CLASS" if not official_source else "IDENTITY_CONFLICT" if conflicts else "FEWER_THAN_TWO_STRONG_MATCHES"
    return {
        "candidate_domain": domain_of(candidate_url),
        "candidate_url": candidate_url,
        "result_classification": classification,
        "identity_matches": sorted(set(matches)),
        "identity_conflicts": conflicts,
        "verification_score": round(min(1.0, len(set(matches)) / 4), 3),
        "official_website_confidence": 1.0 if verified else 0.5 if matches else 0.0,
        "exact_location_page_confidence": 1.0 if verified else 0.0,
        "official_facility_page_url": candidate_url if verified else "",
        "status": status,
        "verified": verified,
        "rejection_reason": rejection_reason,
        "search_rank_observed": search_rank,
    }


def assess_identity_change(
    identity: Mapping[str, Any],
    *,
    website_name: str = "",
    website_address: str = "",
    website_phone: str = "",
    website_status: str = "",
    effective_date: str = "",
) -> Dict[str, Any]:
    authoritative_name = _clean(identity.get("legal_name"))
    authoritative_address = normalize_text(_clean(identity.get("street_address")))
    authoritative_phone = norm_phone_digits(_clean(identity.get("public_phone")))
    current_address = normalize_text(website_address)
    current_phone = norm_phone_digits(website_phone)
    name_changed = bool(website_name and authoritative_name and normalize_text(website_name) != normalize_text(authoritative_name))
    address_matches = bool(current_address and authoritative_address == current_address)
    phone_matches = bool(current_phone and authoritative_phone and current_phone[-7:] == authoritative_phone[-7:])
    moved = bool(current_address and authoritative_address and current_address != authoritative_address)
    closed = normalize_text(website_status) in {"closed", "permanently closed", "license closed"}
    resolved_rename = name_changed and address_matches and phone_matches and not closed
    unresolved = closed or moved or (name_changed and not resolved_rename)
    return {
        "previous_name": authoritative_name if name_changed else "",
        "current_name": website_name if name_changed else authoritative_name,
        "effective_date": effective_date,
        "name_changed": name_changed,
        "moved": moved,
        "closed": closed,
        "identity_resolved": not unresolved,
        "unresolved_identity_conflict": unresolved,
        "conflict_notes": "CLOSED_FACILITY" if closed else "MOVED_FACILITY" if moved else "UNRESOLVED_NAME_CHANGE" if unresolved else "",
    }


def classify_image_content(image: Mapping[str, Any]) -> str:
    text = normalize_text(" ".join(_clean(image.get(key)) for key in ("url", "alt_text", "title", "caption", "nearby_heading", "image_role")))
    category_terms = {
        "logo": ("logo", "favicon", "brandmark"),
        "floor plan": ("floor plan", "floorplan"),
        "map": (" map ", "directions"),
        "illustration": ("illustration", "rendering", "graphic"),
        "staff": ("staff", "team", "nurse", "doctor", "headshot"),
        "resident lifestyle": ("resident", "senior lifestyle", "caregiver"),
        "exterior": ("exterior", "building", "facade"),
        "entrance": ("entrance", "entry"),
        "lobby": ("lobby", "reception"),
        "resident room": ("resident room", "bedroom", "suite"),
        "dining": ("dining", "restaurant"),
        "rehabilitation": ("rehab", "therapy", "gym"),
        "activity area": ("activity", "game room"),
        "garden": ("garden", "courtyard"),
        "walking path": ("walking path", "trail"),
        "amenity": ("amenity", "salon", "library"),
        "campus": ("campus",),
    }
    padded = f" {text} "
    for category, terms in category_terms.items():
        if any(term in padded for term in terms):
            return category
    return "unknown"


def assess_display_rights(image: Mapping[str, Any]) -> str:
    explicit = _clean(image.get("display_rights_status")).upper()
    if explicit:
        return explicit
    if image.get("owner_authorized") is True:
        return "OWNER_AUTHORIZED"
    if image.get("licensed_external") is True:
        return "LICENSED_EXTERNAL"
    if image.get("official_terms_allow_display") is True:
        return "OFFICIAL_DISPLAY_ALLOWED"
    if image.get("terms_prohibit_display") is True:
        return "NOT_DISPLAYABLE"
    if image.get("official_source") is True:
        return "OFFICIAL_SOURCE_TERMS_UNCLEAR"
    return "UNKNOWN"


def evaluate_image_candidate(
    image: Mapping[str, Any],
    *,
    official_facility_page_url: str,
    exact_location_verified: bool,
    reuse_count: int = 1,
) -> Dict[str, Any]:
    category = classify_image_content(image)
    rights = assess_display_rights(image)
    image_url = _clean(image.get("url"))
    reachable = image.get("reachable") is not False and bool(image_url)
    text = normalize_text(" ".join((_clean(image.get("url")), _clean(image.get("alt_text")), _clean(image.get("title")))))
    stock = any(token in text for token in ("pexels", "unsplash", "shutterstock", "getty", "istock", "stock"))
    same_domain = domain_of(image_url) == domain_of(official_facility_page_url)
    rejection_reason = ""
    if not reachable:
        rejection_reason = "BROKEN_IMAGE"
    elif reuse_count > 1:
        rejection_reason = "CORPORATE_OR_STOCK_IMAGE"
    elif stock:
        rejection_reason = "CORPORATE_OR_STOCK_IMAGE"
    elif category not in ELIGIBLE_PRIMARY_CATEGORIES:
        rejection_reason = f"INELIGIBLE_CONTENT_{category.upper().replace(' ', '_')}"
    elif not same_domain:
        rejection_reason = "IMAGE_NOT_ON_OFFICIAL_DOMAIN"
    elif not exact_location_verified:
        rejection_reason = "LOCATION_PAGE_UNVERIFIED"
    elif rights not in DISPLAYABLE_RIGHTS:
        rejection_reason = "DISPLAY_RIGHTS_UNCLEAR"

    verified = not rejection_reason
    if verified:
        status = "VERIFIED"
    elif rejection_reason == "DISPLAY_RIGHTS_UNCLEAR" and exact_location_verified and category in ELIGIBLE_PRIMARY_CATEGORIES:
        status = "PROVISIONAL"
    elif rejection_reason in {"LOCATION_PAGE_UNVERIFIED", "IMAGE_NOT_ON_OFFICIAL_DOMAIN"}:
        status = "AMBIGUOUS"
    else:
        status = "REJECTED"
    return {
        **dict(image),
        "image_category": category,
        "image_status": status,
        "verified_facility_specific": verified,
        "image_facility_identity_confidence": 1.0 if verified else 0.5 if exact_location_verified else 0.0,
        "image_content_confidence": 1.0 if category != "unknown" else 0.0,
        "display_rights_status": rights,
        "display_rights_confidence": 1.0 if rights in DISPLAYABLE_RIGHTS or rights == "NOT_DISPLAYABLE" else 0.0,
        "rejection_reason": rejection_reason,
    }


def image_reuse_key(image: Mapping[str, Any]) -> str:
    content_hash = _clean(image.get("file_hash") or image.get("perceptual_hash"))
    if content_hash:
        return content_hash.lower()
    normalized_url = _clean(image.get("url")).split("?", 1)[0].lower()
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest() if normalized_url else ""


def count_image_reuse(images: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    return dict(Counter(key for image in images if (key := image_reuse_key(image))))


def merge_registry_records(existing: Sequence[Mapping[str, Any]], updates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    index = {_clean(row.get("canonical_facility_id")): dict(row) for row in existing if _clean(row.get("canonical_facility_id"))}
    for update in updates:
        canonical_id = _clean(update.get("canonical_facility_id"))
        if not canonical_id:
            continue
        prior = index.get(canonical_id, {})
        index[canonical_id] = {**prior, **dict(update)}
    return [index[key] for key in sorted(index)]


def prioritize_facilities(
    facilities: Iterable[Mapping[str, Any]],
    *,
    recommendation_ids: Iterable[str] = (),
    launch_markets: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    recommendation_set = {_clean(item) for item in recommendation_ids}
    market_set = {normalize_text(item) for item in launch_markets}

    def priority(row: Mapping[str, Any]) -> tuple[int, str]:
        canonical_id = _clean(row.get("canonical_facility_id") or row.get("canonical_id"))
        market = normalize_text(_clean(row.get("market") or row.get("county") or row.get("city")))
        complete_identity = all(_clean(row.get(field)) for field in ("facility_name", "address", "city", "state"))
        has_verified_image = _clean(row.get("image_status")).upper() == "VERIFIED"
        has_domain = bool(_clean(row.get("official_domain") or row.get("official_website_url")))
        has_location = bool(_clean(row.get("official_facility_page_url")))
        if canonical_id in recommendation_set:
            rank = 1
        elif market in market_set:
            rank = 2
        elif complete_identity and not has_verified_image:
            rank = 3
        elif has_domain and not has_location:
            rank = 4
        else:
            rank = 5
        return rank, canonical_id

    return [dict(row) for row in sorted(facilities, key=priority)]


def downgrade_stale_record(record: Mapping[str, Any], *, conflict_detected: bool = False, image_reachable: bool = True) -> Dict[str, Any]:
    updated = dict(record)
    if _clean(record.get("image_status")).upper() != "VERIFIED":
        return updated
    if conflict_detected or not image_reachable:
        updated["image_status"] = "AMBIGUOUS" if conflict_detected else "REJECTED"
        updated["verified_facility_specific"] = False
        updated["rejection_reason"] = "IDENTITY_CONFLICT" if conflict_detected else "BROKEN_IMAGE"
        updated["last_checked_at"] = utc_now_iso()
    return updated


def coverage_summary(records: Iterable[Mapping[str, Any]], *, total_facilities: int) -> Dict[str, Any]:
    rows = list(records)
    def effective_status(row: Mapping[str, Any]) -> str:
        status = _clean(row.get("image_status")).upper() or "MISSING"
        rights = _clean(row.get("display_rights_status")).upper()
        if status == "VERIFIED" and rights not in DISPLAYABLE_RIGHTS:
            return "PROVISIONAL"
        return status

    status_counts = Counter(effective_status(row) for row in rows)
    verified = sum(
        1
        for row in rows
        if _clean(row.get("image_status")).upper() == "VERIFIED"
        and row.get("verified_facility_specific") is True
        and _clean(row.get("display_rights_status")).upper() in DISPLAYABLE_RIGHTS
    )
    rights_uncertain = sum(
        1
        for row in rows
        if _clean(row.get("primary_image_url"))
        and _clean(row.get("display_rights_status")).upper() in {"", "UNKNOWN", "OFFICIAL_SOURCE_TERMS_UNCLEAR"}
    )
    broken = sum(1 for row in rows if _clean(row.get("rejection_reason")).upper() == "BROKEN_IMAGE" or _clean(row.get("image_probe_status")).upper() in {"HTTP_ERROR", "FETCH_FAILED"})
    searched = sum(1 for row in rows if row.get("search_queries_executed") or row.get("checked_sources"))
    exact_pages = sum(1 for row in rows if _clean(row.get("official_facility_page_url")))
    official_domains = sum(1 for row in rows if _clean(row.get("official_domain") or row.get("official_website_url")))
    authoritative = sum(1 for row in rows if row.get("authoritative_identity_sources") or _clean(row.get("facility_name")))

    by_market: Dict[str, Counter[str]] = defaultdict(Counter)
    by_operator: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        state = effective_status(row)
        market = _clean(row.get("market") or row.get("county") or row.get("city")).upper() or "UNKNOWN"
        operator = _clean(row.get("operator_name")).upper() or "UNKNOWN"
        by_market[market][state] += 1
        by_operator[operator][state] += 1

    def top_reasons(field: str) -> List[Dict[str, Any]]:
        counts = Counter(_clean(row.get(field)) for row in rows if _clean(row.get(field)))
        return [{"reason": reason, "count": count} for reason, count in counts.most_common(10)]

    processing_times = [float(row.get("processing_time_seconds")) for row in rows if isinstance(row.get("processing_time_seconds"), (int, float))]
    now = utc_now_iso()
    return {
        "generated_at_utc": now,
        "pipeline_version": PIPELINE_VERSION,
        "total_facilities": total_facilities,
        "facilities_with_authoritative_identity": authoritative,
        "facilities_searched": searched,
        "official_domains_found": official_domains,
        "exact_facility_pages_verified": exact_pages,
        "operator_only_pages_found": sum(1 for row in rows if _clean(row.get("identity_status")) == "OFFICIAL_OPERATOR_FOUND_LOCATION_UNVERIFIED"),
        "verified_images": verified,
        "provisional_images": status_counts["PROVISIONAL"],
        "ambiguous_images": status_counts["AMBIGUOUS"],
        "rejected_images": status_counts["REJECTED"],
        "missing_images": max(status_counts["MISSING"] + status_counts["UNKNOWN"], total_facilities - len(rows)),
        "display_rights_uncertain_images": rights_uncertain,
        "broken_images": broken,
        "percentage_verified": round((verified / total_facilities * 100) if total_facilities else 0.0, 3),
        "coverage_by_market": {key: dict(value) for key, value in sorted(by_market.items())},
        "coverage_by_operator": {key: dict(value) for key, value in sorted(by_operator.items())},
        "top_search_failure_reasons": top_reasons("search_failure_reason"),
        "top_identity_conflict_reasons": top_reasons("conflict_notes"),
        "top_image_rejection_reasons": top_reasons("rejection_reason"),
        "average_processing_time_seconds": round(sum(processing_times) / len(processing_times), 3) if processing_times else 0.0,
        "records_due_for_recheck": sum(1 for row in rows if _clean(row.get("next_check_at")) and _clean(row.get("next_check_at")) <= now),
    }


def serialize_evidence(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
