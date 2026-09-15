from __future__ import annotations

import ipaddress
import hashlib
import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from sqlalchemy import func

from app.database import SessionLocal
from app.models.supplier_intelligence import SupplierVerificationObservation, SupplierVerificationRun


USER_AGENT = "Oomnik Supplier Verification Agent/1.0 (+https://optime-nursing.onrender.com)"
LOCAL_TERMS = ("las vegas", "henderson", "north las vegas", "clark county", "southern nevada")
COMMON_NAME_TERMS = {
    "and", "care", "company", "health", "healthcare", "home", "las", "llc", "nevada",
    "of", "services", "the", "vegas",
}
OFFICIAL_DOMAINS = (
    "cms.gov", "data.cms.gov", "nv.gov", "nvsos.gov", "nvbar.org", "finra.org",
)
RATING_DOMAINS = ("google.com", "yelp.com", "bbb.org")


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int | None
    text: str
    error: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unescape(str(value or "")).lower()).strip()


def _name_tokens(name: str) -> list[str]:
    return [token for token in _norm(name).split() if len(token) >= 4 and token not in COMMON_NAME_TERMS][:8]


def _strip_html(body: str) -> str:
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.I | re.S)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.I | re.S)
    return _norm(re.sub(r"<[^>]+>", " ", body))


def _safe_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return False
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # DNS failure is recorded by fetch; it is not an SSRF bypass.
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            return False
    return True


def fetch_source(session: requests.Session, url: str, timeout: float = 12.0) -> FetchResult:
    if not _safe_public_url(url):
        return FetchResult(url, url, None, "", "UNSAFE_OR_INVALID_URL")
    try:
        current_url = url
        response = None
        for _ in range(4):
            response = session.get(
                current_url,
                timeout=(5.0, timeout),
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"},
                allow_redirects=False,
            )
            if int(response.status_code) not in {301, 302, 303, 307, 308}:
                break
            location = str((getattr(response, "headers", {}) or {}).get("Location") or "").strip()
            next_url = urljoin(current_url, location)
            if not location or not _safe_public_url(next_url):
                return FetchResult(url, current_url, int(response.status_code), "", "UNSAFE_OR_INVALID_REDIRECT")
            current_url = next_url
        assert response is not None
        body = response.text or ""
        if len(body) > 2_000_000:
            body = body[:2_000_000]
        return FetchResult(url, current_url, int(response.status_code), _strip_html(body))
    except requests.RequestException as exc:
        return FetchResult(url, url, None, "", f"{exc.__class__.__name__}:{str(exc)[:180]}")


def _source_kind(url: str, website: str | None) -> str:
    host = (urlparse(url).hostname or "").lower()
    website_host = (urlparse(website or "").hostname or "").lower()
    if any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_DOMAINS):
        return "OFFICIAL"
    if any(host == domain or host.endswith("." + domain) for domain in RATING_DOMAINS):
        return "REPUTATION"
    if website_host and (host == website_host or host.endswith("." + website_host)):
        return "FIRST_PARTY"
    return "INDEPENDENT_DISCOVERY"


def _identity_match(text: str, supplier_name: str) -> bool:
    tokens = _name_tokens(supplier_name)
    if not tokens:
        return False
    required = 1 if len(tokens) == 1 else min(2, len(tokens))
    return sum(token in text for token in tokens) >= required


def _location_match(text: str) -> bool:
    return any(term in text for term in LOCAL_TERMS)


def _credential_observation(record: dict[str, Any], text: str, kind: str) -> dict[str, Any] | None:
    if kind != "OFFICIAL":
        return None
    for credential in record.get("licenses") or []:
        identifier = _norm(credential.get("identifier"))
        if identifier and identifier in text:
            return {
                "authority": credential.get("authority"),
                "identifier": credential.get("identifier"),
                "identifier_observed_on_official_source": True,
                "active_term_observed": bool(re.search(r"\b(active|current|certified)\b", text)),
            }
    return None


def verify_supplier_record(
    record: dict[str, Any],
    *,
    session: requests.Session | None = None,
    timeout: float = 12.0,
    max_sources: int = 4,
) -> dict[str, Any]:
    session = session or requests.Session()
    website = str((record.get("branch") or {}).get("website") or "").strip() or None
    urls = []
    if website:
        urls.append(website)
    urls.extend(str(url).strip() for url in record.get("evidence_refs") or [] if str(url).startswith("http"))
    urls = list(dict.fromkeys(urls))[:max_sources]

    observations: list[dict[str, Any]] = []
    for url in urls:
        result = fetch_source(session, url, timeout=timeout)
        kind = _source_kind(result.final_url or url, website)
        identity = bool(result.status_code and result.status_code < 400 and _identity_match(result.text, record.get("brand_name") or ""))
        location = bool(result.status_code and result.status_code < 400 and _location_match(result.text))
        observations.append({
            "requested_url": url,
            "final_url": result.final_url,
            "source_kind": kind,
            "http_status": result.status_code,
            "reachable": bool(result.status_code and result.status_code < 400),
            "identity_match": identity,
            "las_vegas_valley_match": location,
            "credential": _credential_observation(record, result.text, kind),
            "error": result.error,
            "checked_at": _now(),
        })

    matched = [item for item in observations if item["identity_match"] and item["las_vegas_valley_match"]]
    independent_kinds = {item["source_kind"] for item in matched}
    official_identity = any(item["source_kind"] == "OFFICIAL" for item in matched)
    corroborated_identity = len(matched) >= 2 and len(independent_kinds) >= 2
    credential_verified = any(
        item.get("credential", {}).get("identifier_observed_on_official_source") is True
        and item.get("credential", {}).get("active_term_observed") is True
        for item in observations if isinstance(item.get("credential"), dict)
    )

    if credential_verified:
        stage = "OFFICIAL_CREDENTIAL_OBSERVED"
    elif official_identity or corroborated_identity:
        stage = "IDENTITY_AND_MARKET_CORROBORATED"
    elif matched:
        stage = "SINGLE_SOURCE_MATCH"
    elif observations:
        stage = "NO_MATCH_OBSERVED"
    else:
        stage = "NO_SOURCE_AVAILABLE"

    return {
        "stage": stage,
        "checked_at": _now(),
        "sources_attempted": len(observations),
        "sources_reachable": sum(item["reachable"] for item in observations),
        "identity_market_matches": len(matched),
        "official_identity_observed": official_identity,
        "corroborated_identity": corroborated_identity,
        "official_credential_observed": credential_verified,
        "observations": observations,
        "publication_unchanged": True,
        "case_readiness_unchanged": True,
    }


def verification_priority(record: dict[str, Any]) -> tuple[int, int, str, str]:
    last_checked = str(record.get("_last_verified_at") or "")
    critical = 0 if record.get("involvement") == "OUTCOME_CRITICAL" else 1
    never_checked = 0 if not record.get("verification") and not last_checked else 1
    return (never_checked, critical, last_checked, str(record.get("brand_name") or "").lower())


def select_verification_batch(
    records: Iterable[dict[str, Any]],
    limit: int,
    *,
    last_checked_by_supplier: dict[str, datetime] | None = None,
) -> list[dict[str, Any]]:
    last_checked_by_supplier = last_checked_by_supplier or {}
    candidates = []
    for record in records:
        if (record.get("publication") or {}).get("status") not in {"CANDIDATE", "LIMITED"}:
            continue
        copied = dict(record)
        checked_at = last_checked_by_supplier.get(str(record.get("supplier_id") or ""))
        if checked_at:
            copied["_last_verified_at"] = checked_at.isoformat()
        candidates.append(copied)
    return sorted(candidates, key=verification_priority)[: max(0, limit)]


def last_checked_by_supplier() -> dict[str, datetime]:
    """Return the latest persisted check per supplier so scheduled runs rotate coverage."""
    db = SessionLocal()
    try:
        rows = db.query(
            SupplierVerificationObservation.supplier_id,
            func.max(SupplierVerificationObservation.checked_at),
        ).group_by(SupplierVerificationObservation.supplier_id).all()
        return {str(supplier_id): checked_at for supplier_id, checked_at in rows if checked_at is not None}
    finally:
        db.close()


def persist_verification_results(results: list[dict[str, Any]]) -> dict[str, int]:
    """Append source observations to PostgreSQL/SQLite; repeated identical evidence is idempotent."""
    db = SessionLocal()
    run = SupplierVerificationRun(status="RUNNING")
    db.add(run)
    db.flush()
    inserted = 0
    duplicates = 0
    try:
        for item in results:
            verification = item["verification"]
            for observation in verification.get("observations") or []:
                stable = json.dumps({
                    "source_kind": observation.get("source_kind"),
                    "http_status": observation.get("http_status"),
                    "reachable": observation.get("reachable"),
                    "identity_match": observation.get("identity_match"),
                    "las_vegas_valley_match": observation.get("las_vegas_valley_match"),
                    "credential": observation.get("credential"),
                }, sort_keys=True)
                digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
                exists = db.query(SupplierVerificationObservation.id).filter_by(
                    supplier_id=item["supplier_id"],
                    source_url=observation.get("final_url") or observation.get("requested_url") or "UNKNOWN",
                    content_hash=digest,
                ).first()
                if exists:
                    duplicates += 1
                    continue
                db.add(SupplierVerificationObservation(
                    run_id=run.id,
                    supplier_id=item["supplier_id"],
                    supplier_name=item["brand_name"],
                    stage=verification["stage"],
                    source_url=observation.get("final_url") or observation.get("requested_url") or "UNKNOWN",
                    source_kind=observation.get("source_kind") or "UNKNOWN",
                    http_status=observation.get("http_status"),
                    reachable=1 if observation.get("reachable") else 0,
                    identity_match=1 if observation.get("identity_match") else 0,
                    market_match=1 if observation.get("las_vegas_valley_match") else 0,
                    credential_observed=1 if (observation.get("credential") or {}).get("identifier_observed_on_official_source") else 0,
                    content_hash=digest,
                    evidence_json=json.dumps(observation, sort_keys=True),
                ))
                inserted += 1
        run.status = "SUCCESS"
        run.records_processed = len(results)
        run.source_requests = sum(len(item["verification"].get("observations") or []) for item in results)
        run.reachable_sources = sum(sum(1 for o in item["verification"].get("observations") or [] if o.get("reachable")) for item in results)
        counts: dict[str, int] = {}
        for item in results:
            stage = item["verification"]["stage"]
            counts[stage] = counts.get(stage, 0) + 1
        run.stage_counts_json = json.dumps(counts, sort_keys=True)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"run_id": int(run.id), "observations_inserted": inserted, "duplicates_skipped": duplicates}
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"supplier verification persistence failed: {exc}") from exc
    finally:
        db.close()


def supplier_verification_status(db: Any) -> dict[str, Any]:
    latest = db.query(SupplierVerificationRun).order_by(SupplierVerificationRun.id.desc()).first()
    stage_rows = db.query(
        SupplierVerificationObservation.stage,
        func.count(SupplierVerificationObservation.id),
    ).group_by(SupplierVerificationObservation.stage).all()
    return {
        "agent": "oomnik-supplier-verification-agent",
        "has_completed_run": bool(latest and latest.status == "SUCCESS"),
        "latest_run": None if latest is None else {
            "id": latest.id,
            "status": latest.status,
            "records_processed": latest.records_processed,
            "source_requests": latest.source_requests,
            "reachable_sources": latest.reachable_sources,
            "stage_counts": json.loads(latest.stage_counts_json or "{}"),
            "started_at": latest.started_at,
            "completed_at": latest.completed_at,
        },
        "stored_observations": db.query(SupplierVerificationObservation).count(),
        "observation_stage_counts": {stage: count for stage, count in stage_rows},
    }
