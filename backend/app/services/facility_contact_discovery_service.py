from __future__ import annotations

"""Best-effort discovery of a facility's own marketing/admissions email address, from
the facility's own public website only -- never guessed, never a third-party
directory's contact form. This is what makes automated outreach (facility_outreach_
service.py) possible without OPTIME already holding facility contact data, which,
as of this writing, exists for none of the ~377 canonical Nevada facilities.

Reuses the live web-lookup primitives already built for evidence research
(decision_research_worker.py) rather than inventing a second HTTP/search stack.
"""

import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from sqlalchemy.orm import Session

from app.models.facility_outreach import FacilityContact
from app.services.decision_research_worker import _candidate_official_url, _fetch
from app.services.facility_parameter_service import get_canonical_facility_index

_MAILTO_RE = re.compile(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_IMAGE_LIKE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
_SKIP_EMAIL_DOMAINS = ("example.com", "sentry.io", "wixpress.com", "godaddy.com", "schema.org")

# Ordered by how directly the mailbox is meant for a prospective resident's family
# asking about rooms/pricing -- the outreach OPTIME sends is exactly that ask.
_ROLE_BY_LOCAL_PART_HINT = (
    ("marketing", "MARKETING_SALES"),
    ("sales", "MARKETING_SALES"),
    ("leasing", "MARKETING_SALES"),
    ("admissions", "ADMISSIONS"),
    ("tours", "ADMISSIONS"),
    ("info", "GENERAL"),
    ("hello", "GENERAL"),
    ("contact", "GENERAL"),
)
_CONTACT_PATH_HINTS = ("contact", "admission", "tour", "schedule")
_MAX_CONTACT_PAGES = 3


def get_known_contact(db: Session, canonical_facility_id: str) -> Optional[FacilityContact]:
    return (
        db.query(FacilityContact)
        .filter(FacilityContact.canonical_facility_id == canonical_facility_id)
        .order_by(FacilityContact.id.desc())
        .first()
    )


def _role_for_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    for hint, role in _ROLE_BY_LOCAL_PART_HINT:
        if hint in local:
            return role
    return "UNKNOWN"


def _is_plausible_contact_email(email: str) -> bool:
    if email.endswith(_IMAGE_LIKE_SUFFIXES):
        return False
    domain = email.split("@", 1)[-1].lower()
    return not any(domain == skip or domain.endswith("." + skip) for skip in _SKIP_EMAIL_DOMAINS)


def _extract_emails(html: str) -> List[str]:
    found = {m.lower() for m in _MAILTO_RE.findall(html)}
    found.update(m.lower() for m in _EMAIL_RE.findall(html))
    return [email for email in found if _is_plausible_contact_email(email)]


def _same_domain_contact_page_links(html: str, base_url: str) -> List[str]:
    domain = urlparse(base_url).netloc
    hrefs = re.findall(r'href="([^"]+)"', html, flags=re.IGNORECASE)
    seen = set()
    out: List[str] = []
    for href in hrefs:
        if not any(hint in href.lower() for hint in _CONTACT_PATH_HINTS):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).netloc != domain or absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
        if len(out) >= _MAX_CONTACT_PAGES:
            break
    return out


def _rank_candidates(candidates: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    """candidates: (email, source_url) pairs. Prefers role-specific mailboxes, then
    the earliest-found page (the official homepage over a deeper contact page)."""
    if not candidates:
        return None
    role_rank = {"MARKETING_SALES": 0, "ADMISSIONS": 1, "GENERAL": 2, "UNKNOWN": 3}
    return min(candidates, key=lambda pair: (role_rank[_role_for_email(pair[0])], pair[0]))


def discover_contact(db: Session, canonical_facility_id: str) -> Optional[FacilityContact]:
    """Live, on-demand lookup -- not a batch crawl. Returns the already-known contact
    if one exists, otherwise looks at the facility's own official website (and up to a
    few of its own contact/admissions pages) for a real email address. Returns None,
    never a fabricated address, when nothing is found; the caller must treat that as
    a genuine outcome to report, not retry silently."""
    existing = get_known_contact(db, canonical_facility_id)
    if existing is not None:
        return existing

    facility = get_canonical_facility_index().get(canonical_facility_id)
    if not facility:
        return None
    facility_name = str(facility.get("facility_name") or facility.get("name") or "")
    city = str(facility.get("city") or "")

    official_url = _candidate_official_url(facility_name, city, canonical_facility_id)
    if not official_url:
        return None

    try:
        homepage_html, homepage_status = _fetch(official_url)
    except Exception:
        return None

    candidates: List[Tuple[str, str]] = []
    if homepage_status == 200:
        candidates.extend((email, official_url) for email in _extract_emails(homepage_html))
        for page_url in _same_domain_contact_page_links(homepage_html, official_url):
            try:
                page_html, page_status = _fetch(page_url)
            except Exception:
                continue
            if page_status != 200:
                continue
            candidates.extend((email, page_url) for email in _extract_emails(page_html))

    best = _rank_candidates(candidates)
    if not best:
        return None
    email, source_url = best

    contact = FacilityContact(
        canonical_facility_id=canonical_facility_id,
        email=email,
        contact_role=_role_for_email(email),
        source_url=source_url,
        source="WEBSITE_DISCOVERY",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
