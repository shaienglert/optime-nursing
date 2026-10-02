"""Research obligations are independent of search traffic and of ranking scores."""
from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urlparse

VERSION = "research-coverage-v1"
RECORD_TYPE = "institutional_research_observation"
EXCLUDED_DOMAINS = {"aplaceformom.com", "caring.com", "senioradvisor.com", "seniorly.com", "seniorhomes.com", "carepatrol.com"}
TOPICS = {
    "official_complaints": {"label": "Known official complaints and complaint-related findings · last 12 months", "ttl_hours": 24, "source": "State regulator / CMS", "next_action": "Check published complaint investigations, findings, correction and enforcement; distinguish allegations from findings."},
    "regulatory_history": {"label": "Licensing, inspections and corrective action", "ttl_hours": 24, "source": "Nevada HCQC / ALiS", "next_action": "Refresh the exact license record and inspection documents; verify correction rather than infer it from a plan."},
    "cms_quality": {"label": "CMS / Medicare quality and staffing", "ttl_hours": 168, "source": "CMS / Medicare", "next_action": "Refresh CMS provider data by CCN, including SFF and abuse flags. Medicare and CMS are one source."},
    "google_reviews": {"label": "Google Maps consumer rating", "ttl_hours": 24, "source": "Google Maps", "next_action": "Use licensed Places API, exact facility identity and required attribution; do not persist restricted content."},
    "independent_ratings": {"label": "Independent ratings", "ttl_hours": 168, "source": "U.S. News / Newsweek", "next_action": "Obtain redistribution permission and a supported feed; preserve original scale and rating year."},
    "accreditation": {"label": "Accreditation", "ttl_hours": 168, "source": "Joint Commission", "next_action": "Verify exact accredited location, program and validity through an authorized source."},
    "staffing_operations": {"label": "Day/night staffing and continuity", "ttl_hours": 168, "source": "Regulator / verified provider documents", "next_action": "Collect dated shift counts and turnover definitions. Do not invent a national assisted-living ratio or turnover threshold."},
}


def permitted_source(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and bool(host) and not any(host == d or host.endswith("." + d) for d in EXCLUDED_DOMAINS)


def parse_date(value) -> date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def complaint_window(today: date) -> tuple[date, date]:
    # Calendar year, not 365 days (leap years must not shift the window).
    try:
        start = today.replace(year=today.year - 1)
    except ValueError:
        start = today.replace(year=today.year - 1, day=28)
    return start, today


def observation_status(record: dict | None, topic: str, now: datetime) -> str:
    if not record:
        return "NOT_CHECKED"
    status = str(record.get("status") or "UNKNOWN")
    try:
        observed = datetime.fromisoformat(str(record.get("observed_at") or "").replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        age = (now - observed).total_seconds()
    except ValueError:
        return "UNKNOWN"
    if age < 0 or age > TOPICS[topic]["ttl_hours"] * 3600:
        return "STALE"
    if status in {"VERIFIED", "CHECKED_NO_PUBLISHED_FINDINGS", "PARTIAL"}:
        if record.get("identity_verified") is not True or not permitted_source(record.get("source_url", "")):
            return "UNKNOWN"
        # A fetched page without extracted fields is not delivered evidence.
        if not record.get("data"):
            return "UNKNOWN"
    return status
