from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

NAME_STOPWORDS = {
    "the",
    "and",
    "at",
    "of",
    "inc",
    "llc",
}
DOMAIN_IDENTITY_STOPWORDS = NAME_STOPWORDS.union({
    "care",
    "center",
    "community",
    "facility",
    "health",
    "home",
    "living",
    "nursing",
    "rehabilitation",
    "senior",
    "skilled",
})

NAME_SYNONYMS = {
    "rehab": "rehabilitation",
    "rehabilitation": "rehabilitation",
    "healthcare": "health",
    "health": "health",
    "centre": "center",
    "ctr": "center",
    "&": "and",
}

ADDRESS_SYNONYMS = {
    "street": "st",
    "st": "st",
    "avenue": "ave",
    "ave": "ave",
    "road": "rd",
    "rd": "rd",
    "boulevard": "blvd",
    "blvd": "blvd",
    "drive": "dr",
    "dr": "dr",
    "lane": "ln",
    "ln": "ln",
    "northwest": "nw",
    "northeast": "ne",
    "southwest": "sw",
    "southeast": "se",
}

RASTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
LOGO_KEYWORDS = {"logo", "icon", "favicon", "sprite", "pixel"}
BADGE_KEYWORDS = {"award", "awards", "badge", "certified", "workplace", "accreditation"}
HEADSHOT_KEYWORDS = {"staff", "team", "doctor", "nurse", "portrait", "headshot", "provider"}
STOCK_KEYWORDS = {"pexels", "unsplash", "shutterstock", "getty", "istock", "pixabay", "freepik", "stock"}
GENERIC_SERVICE_IMAGE_KEYWORDS = {
    "skillednursing",
    "skilled",
    "nursing",
    "occupationaltherapy",
    "occupational",
    "physicaltherapy",
    "physical",
    "speechtherapy",
    "speech",
    "therapy",
    "rehab",
    "rehabilitation",
    "senior",
    "care",
    "health",
}
FACILITY_PHOTO_KEYWORDS = {
    "building",
    "lobby",
    "room",
    "rooms",
    "interior",
    "exterior",
    "entrance",
    "garden",
    "courtyard",
}
FACILITY_IDENTITY_STOPWORDS = GENERIC_SERVICE_IMAGE_KEYWORDS.union({"center", "centre", "facility", "community", "inc", "llc"})

DIRECTORY_DOMAINS = {
    "aplaceformom.com",
    "assistedliving.org",
    "caring.com",
    "nursinghomedatabase.com",
    "nursinghomes.com",
    "seniorhousingnet.com",
    "seniorlivingflorida.org",
    "seniorly.com",
}
REVIEW_DOMAINS = {"bbb.org", "glassdoor.com", "indeed.com", "yelp.com"}
SOCIAL_DOMAINS = {"facebook.com", "instagram.com", "linkedin.com", "tiktok.com", "x.com", "youtube.com"}
GOVERNMENT_SUFFIXES = (".gov", ".gov.us")


def classify_search_result(candidate_url: str, page_text: str = "") -> str:
    domain = domain_of(candidate_url)
    normalized_page = normalize_text(page_text)
    if domain.endswith(GOVERNMENT_SUFFIXES):
        return "GOVERNMENT_PAGE"
    if any(domain == item or domain.endswith(f".{item}") for item in DIRECTORY_DOMAINS):
        return "DIRECTORY"
    if any(domain == item or domain.endswith(f".{item}") for item in REVIEW_DOMAINS):
        return "REVIEW_WEBSITE"
    if any(domain == item or domain.endswith(f".{item}") for item in SOCIAL_DOMAINS):
        return "SOCIAL_MEDIA_PAGE"
    if any(token in normalized_page for token in ("news release", "press release", "reported by")):
        return "NEWS_ARTICLE"
    return "POSSIBLE_OFFICIAL_PAGE"


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str) -> str:
    lowered = value.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return normalize_spaces(lowered)


def norm_phone_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def domain_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def _identity_domain_label(candidate_url: str) -> str:
    labels = [label for label in domain_of(candidate_url).split(".") if label]
    if len(labels) >= 2:
        return labels[-2]
    return labels[0] if labels else ""


def _domain_affinity_score(facility_name: str, candidate_url: str) -> float:
    host_root = _identity_domain_label(candidate_url)
    if not host_root:
        return 0.0

    facility_tokens = [token for token in _tokenize_name(facility_name) if len(token) >= 4 and token not in DOMAIN_IDENTITY_STOPWORDS]
    if not facility_tokens:
        return 0.0

    hits = sum(1 for token in facility_tokens if token in host_root)
    score = hits / len(facility_tokens)
    if len(facility_tokens) >= 2:
        acronym = "".join(token[0] for token in facility_tokens[:2])
        if len(acronym) >= 2 and host_root.startswith(acronym):
            score = max(score, 0.2)
    return score


def _tokenize_name(value: str) -> List[str]:
    tokens = []
    for token in normalize_text(value).split():
        mapped = NAME_SYNONYMS.get(token, token)
        if len(mapped) >= 2 and mapped not in NAME_STOPWORDS:
            tokens.append(mapped)
    return tokens


def _tokenize_address(value: str) -> List[str]:
    tokens = []
    for token in normalize_text(value).split():
        mapped = ADDRESS_SYNONYMS.get(token, token)
        if mapped:
            tokens.append(mapped)
    return tokens


def facility_name_similarity(name_variant: str, page_text: str) -> float:
    candidate_tokens = set(_tokenize_name(name_variant))
    page_tokens = set(_tokenize_name(page_text))
    if not candidate_tokens:
        return 0.0
    matched = sum(1 for token in candidate_tokens if token in page_tokens)
    return matched / len(candidate_tokens)


def address_match_score(address: str, page_text: str, city: str = "", state: str = "") -> float:
    address_tokens = _tokenize_address(address)
    if not address_tokens:
        return 0.0

    normalized_page = normalize_text(page_text)
    normalized_address = " ".join(address_tokens)
    if normalized_address and normalized_address in normalized_page:
        return 1.0

    page_tokens = set(_tokenize_address(page_text))
    matched = sum(1 for token in address_tokens if token in page_tokens)
    overlap = matched / len(address_tokens)
    street_number = address_tokens[0] if address_tokens else ""
    city_match = bool(city and normalize_text(city) in normalized_page)
    state_match = bool(state and normalize_text(state) in normalized_page)
    if street_number and street_number in page_tokens and overlap >= 0.5 and (city_match or state_match):
        return 0.85
    if street_number and street_number in page_tokens and overlap >= 0.35:
        return 0.65
    return overlap


def evaluate_identity_candidate(
    *,
    facility_name: str,
    name_variants: Iterable[str],
    address: str,
    city: str,
    state: str,
    phone: str,
    cms_ccn: str,
    operator_name: str,
    candidate_url: str,
    page_text: str,
    source_type: str,
) -> Dict[str, Any]:
    result_classification = classify_search_result(candidate_url, page_text)
    page_text_normalized = normalize_text(page_text)
    page_digits = re.sub(r"\D", "", page_text)
    name_scores = []
    for variant in [facility_name, *list(name_variants)]:
        variant = str(variant or "").strip()
        if not variant:
            continue
        name_scores.append((variant, facility_name_similarity(variant, page_text)))
    best_name_variant, best_name_score = max(name_scores, key=lambda item: item[1], default=(facility_name, 0.0))

    address_score = address_match_score(address, page_text, city=city, state=state)
    phone_digits = norm_phone_digits(phone)
    phone_match = bool(len(phone_digits) >= 7 and phone_digits[-7:] in page_digits)
    ccn_digits = norm_phone_digits(cms_ccn)
    ccn_match = bool(ccn_digits and ccn_digits in page_digits)
    operator_match = bool(operator_name and facility_name_similarity(operator_name, page_text) >= 0.75)
    city_match = bool(city and normalize_text(city) in page_text_normalized)

    score = 0.0
    score += min(address_score, 1.0) * 0.45
    if phone_match:
        score += 0.3
    if best_name_score >= 0.85:
        score += 0.25
    elif best_name_score >= 0.65:
        score += 0.18
    elif best_name_score >= 0.45:
        score += 0.1
    if operator_match:
        score += 0.08
    if ccn_match:
        score += 0.15
    if city_match:
        score += 0.04
    score = min(score, 1.0)
    domain_affinity_score = _domain_affinity_score(facility_name, candidate_url)
    operator_domain_affinity_score = _domain_affinity_score(operator_name, candidate_url) if operator_name else 0.0
    ranking_score = score + (max(domain_affinity_score, operator_domain_affinity_score) * 0.08)

    verified = (
        (address_score >= 0.8 and (phone_match or best_name_score >= 0.6))
        or (phone_match and best_name_score >= 0.7)
        or ccn_match
    )
    if source_type == "SEARCH_DISCOVERY":
        verified = verified and max(domain_affinity_score, operator_domain_affinity_score) >= 0.15
    if result_classification != "POSSIBLE_OFFICIAL_PAGE":
        verified = False
    partial = not verified and (
        (address_score >= 0.6 and best_name_score >= 0.45)
        or (phone_match and best_name_score >= 0.45)
        or (address_score >= 0.6 and phone_match)
    )

    status = "VERIFIED" if verified and score >= 0.75 else "PARTIAL" if partial else "NOT_VERIFIED"

    return {
        "candidate_url": candidate_url,
        "source_type": source_type,
        "result_classification": result_classification,
        "status": status,
        "score": round(score, 3),
        "ranking_score": round(ranking_score, 3),
        "identity_match_evidence": {
            "matched_name_variant": best_name_variant,
            "name_similarity_score": round(best_name_score, 3),
            "address_match_score": round(address_score, 3),
            "phone_match": phone_match,
            "city_match": city_match,
            "operator_match": operator_match,
            "ccn_match": ccn_match,
            "domain_affinity_score": round(domain_affinity_score, 3),
            "operator_domain_affinity_score": round(operator_domain_affinity_score, 3),
        },
    }


def resolve_best_identity(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = sorted(
        candidates,
        key=lambda item: (
            float(item.get("ranking_score") or item.get("score") or 0.0),
            float(item.get("score") or 0.0),
        ),
        reverse=True,
    )
    verified = [item for item in evaluated if item.get("status") == "VERIFIED"]

    if verified:
        top = verified[0]
        top_domain = domain_of(str(top.get("candidate_url") or ""))
        second = next(
            (
                item
                for item in verified[1:]
                if domain_of(str(item.get("candidate_url") or "")) != top_domain
            ),
            None,
        )
        if second is not None:
            top_rank = float(top.get("ranking_score") or top.get("score") or 0.0)
            second_rank = float(second.get("ranking_score") or second.get("score") or 0.0)
            if abs(top_rank - second_rank) < 0.02:
                return {
                    "identity_status": "AMBIGUOUS",
                    "identity_verified": False,
                    "official_domain_verified": False,
                    "official_website_url": "",
                    "official_facility_page_url": "",
                    "identity_match_evidence": top.get("identity_match_evidence") or {},
                    "identity_candidates_checked": len(evaluated),
                }

        return {
            "identity_status": "VERIFIED",
            "identity_verified": True,
            "official_domain_verified": True,
            "official_website_url": top["candidate_url"],
            "official_facility_page_url": top["candidate_url"],
            "identity_match_evidence": top.get("identity_match_evidence") or {},
            "identity_candidates_checked": len(evaluated),
        }

    partial = evaluated[0] if evaluated else None
    return {
        "identity_status": "PARTIAL" if partial else "NOT_VERIFIED",
        "identity_verified": False,
        "official_domain_verified": False,
        "official_website_url": "",
        "official_facility_page_url": "",
        "identity_match_evidence": (partial or {}).get("identity_match_evidence") or {},
        "identity_candidates_checked": len(evaluated),
    }


def extract_candidate_images(page_url: str, html: str) -> List[Dict[str, str]]:
    images: List[Dict[str, str]] = []

    def add_image(raw_url: str, source_type: str, alt_text: str = "") -> None:
        raw_url = raw_url.strip()
        if not raw_url:
            return
        absolute = urljoin(page_url, raw_url)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            return
        images.append(
            {
                "url": absolute,
                "source_type": source_type,
                "alt_text": alt_text.strip(),
                "source_page_url": page_url,
            }
        )

    for pattern, source_type in [
        (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', "OFFICIAL_OG_IMAGE"),
        (r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', "OFFICIAL_TWITTER_IMAGE"),
    ]:
        for match in re.findall(pattern, html, flags=re.I):
            add_image(match, source_type)

    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, flags=re.I):
        tag = match.group(0)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', tag, flags=re.I)
        add_image(match.group(1), "OFFICIAL_PAGE_IMAGE", alt_match.group(1) if alt_match else "")

    deduped: List[Dict[str, str]] = []
    seen: set[str] = set()
    for image in images:
        if image["url"] in seen:
            continue
        seen.add(image["url"])
        deduped.append(image)
    return deduped


def classify_image_candidate(image: Dict[str, str], facility_name: str, official_page_url: str) -> Dict[str, Any]:
    image_url = str(image.get("url") or "").strip()
    alt_text = str(image.get("alt_text") or "")
    if not image_url:
        return {"status": "REJECTED", "reason": "MISSING_URL", "score": 0.0}

    parsed = urlparse(image_url)
    extension = Path(parsed.path).suffix.lower()
    image_basename = Path(parsed.path.rstrip("/")).name
    url_text = normalize_text(parsed.path.replace("/", " ").replace("-", " ").replace("_", " "))
    alt_norm = normalize_text(alt_text)
    combined = f"{url_text} {alt_norm}".strip()
    combined_tokens = set(combined.split())
    facility_tokens = set(_tokenize_name(facility_name))

    if extension == ".svg":
        return {"status": "REJECTED", "reason": "SVG_NOT_FACILITY_PHOTO", "score": 0.0}
    if not extension and len(image_basename) <= 2:
        return {"status": "REJECTED", "reason": "MALFORMED_IMAGE_PATH", "score": 0.0}
    if any(keyword in combined_tokens for keyword in LOGO_KEYWORDS):
        return {"status": "REJECTED", "reason": "LOGO_OR_ICON", "score": 0.0}
    if any(keyword in combined_tokens for keyword in BADGE_KEYWORDS) or {"top", "work", "place"}.issubset(combined_tokens):
        return {"status": "REJECTED", "reason": "AWARD_OR_BADGE", "score": 0.0}
    if any(keyword in combined_tokens for keyword in HEADSHOT_KEYWORDS):
        return {"status": "REJECTED", "reason": "HEADSHOT_OR_STAFF", "score": 0.0}
    if any(keyword in image_url.lower() or keyword in combined_tokens for keyword in STOCK_KEYWORDS):
        return {"status": "AMBIGUOUS", "reason": "STOCK_LIKE_ASSET", "score": 0.4}

    if extension and extension not in RASTER_EXTENSIONS:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_IMAGE_TYPE", "score": 0.0}

    meaningful_facility_tokens = facility_tokens - FACILITY_IDENTITY_STOPWORDS
    matched_facility_tokens = meaningful_facility_tokens.intersection(combined_tokens)
    facility_name_match = bool(matched_facility_tokens)
    strong_alt_identity = len(meaningful_facility_tokens.intersection(set(alt_norm.split()))) >= min(2, len(meaningful_facility_tokens))
    place_cue_match = bool(FACILITY_PHOTO_KEYWORDS.intersection(combined_tokens))
    generic_activity_asset = bool({"activity", "activities"}.intersection(set(url_text.split()))) and not place_cue_match
    generic_service_only = bool(combined_tokens) and combined_tokens.issubset(GENERIC_SERVICE_IMAGE_KEYWORDS.union({"jpg", "jpeg", "png", "webp", "uploads", "content", "images", "wp", "2022", "2023", "2024", "2025", "2026"}))

    score = 0.0
    if facility_name_match:
        score += 0.55
    if strong_alt_identity:
        score += 0.35
    if place_cue_match:
        score += 0.35
    if domain_of(image_url) == domain_of(official_page_url):
        score += 0.1
    score = min(score, 1.0)

    if generic_service_only and not facility_name_match and not place_cue_match:
        return {"status": "AMBIGUOUS", "reason": "GENERIC_SERVICE_IMAGE", "score": 0.45}
    if generic_activity_asset:
        return {"status": "AMBIGUOUS", "reason": "GENERIC_ACTIVITY_IMAGE", "score": round(score, 3)}

    has_facility_specific_visual_evidence = place_cue_match and (facility_name_match or strong_alt_identity)
    if score >= 0.75 and has_facility_specific_visual_evidence:
        return {"status": "VERIFIED", "reason": "FACILITY_SPECIFIC_IMAGE", "score": round(score, 3)}

    return {"status": "AMBIGUOUS", "reason": "INSUFFICIENT_FACILITY_SPECIFIC_EVIDENCE", "score": round(score, 3)}


def select_primary_image(images: List[Dict[str, str]], facility_name: str, official_page_url: str) -> Dict[str, Any]:
    evaluated: List[Dict[str, Any]] = []
    for image in images:
        classification = classify_image_candidate(image, facility_name=facility_name, official_page_url=official_page_url)
        evaluated.append({**image, **classification})

    verified = sorted((item for item in evaluated if item["status"] == "VERIFIED"), key=lambda item: float(item["score"]), reverse=True)
    ambiguous = sorted((item for item in evaluated if item["status"] == "AMBIGUOUS"), key=lambda item: float(item["score"]), reverse=True)

    if verified:
        top = verified[0]
        return {
            "primary_image_url": top["url"],
            "image_source_url": top["source_page_url"],
            "image_source_type": top["source_type"],
            "image_status": "VERIFIED",
            "verified_facility_specific": True,
            "image_match_evidence": {
                "reason": top["reason"],
                "alt_text": top.get("alt_text") or "",
                "score": top["score"],
            },
            "evaluated_image_count": len(evaluated),
        }

    if ambiguous:
        top = ambiguous[0]
        return {
            "primary_image_url": "",
            "image_source_url": top["source_page_url"],
            "image_source_type": top["source_type"],
            "image_status": "AMBIGUOUS",
            "verified_facility_specific": False,
            "image_match_evidence": {
                "reason": top["reason"],
                "alt_text": top.get("alt_text") or "",
                "score": top["score"],
            },
            "evaluated_image_count": len(evaluated),
        }

    return {
        "primary_image_url": "",
        "image_source_url": "",
        "image_source_type": "",
        "image_status": "UNKNOWN",
        "verified_facility_specific": False,
        "image_match_evidence": {},
        "evaluated_image_count": len(evaluated),
    }
