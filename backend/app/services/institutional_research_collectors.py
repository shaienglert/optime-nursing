"""Official-source collectors. No search result snippet establishes a finding."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import requests

from app.services.cms_service import CMS_INSPECTION_DATASET_ID, CMS_PROVIDER_DATASET_ID
from app.services.research_coverage_contract import complaint_window, parse_date

TIMEOUT = (5, 25)
MAX_BYTES = 250_000_000
CMS_ROOT = "https://data.cms.gov/provider-data"


def _cms_rows(dataset: str):
    metadata = requests.get(f"{CMS_ROOT}/api/1/metastore/schemas/dataset/items/{dataset}", timeout=TIMEOUT)
    metadata.raise_for_status()
    urls = [x.get("downloadURL") for x in metadata.json().get("distribution", []) if x.get("downloadURL")]
    if not urls:
        raise ValueError("CMS distribution unavailable")
    parsed = urlparse(urls[0])
    if parsed.scheme != "https" or parsed.hostname != "data.cms.gov":
        raise ValueError("CMS distribution host not approved")
    with requests.get(urls[0], timeout=TIMEOUT, stream=True) as response:
        response.raise_for_status()
        total = 0
        # Streaming avoids retaining the nationwide CSV in process memory.
        def lines():
            nonlocal total
            for raw in response.iter_lines():
                total += len(raw)
                if total > MAX_BYTES:
                    raise ValueError("CMS dataset exceeds collection budget")
                yield raw.decode("utf-8-sig") + "\n"
        reader = csv.DictReader(lines())
        required = {"CMS Certification Number (CCN)"}
        if dataset == CMS_INSPECTION_DATASET_ID:
            required |= {"Complaint Deficiency", "Survey Date", "Processing Date"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("CMS dataset schema changed")
        yield from reader


class ResearchCollectionContext:
    """One CMS download per batch, not one nationwide download per facility."""
    def __init__(self, now=None):
        self.now = now or datetime.now(timezone.utc)
        self.provider_rows = None
        self.deficiencies = None
        self.cms_error = None
        self.inspection_error = None

    def providers(self):
        if self.provider_rows is None and self.cms_error is None:
            try:
                self.provider_rows = {str(row.get("CMS Certification Number (CCN)", "")).zfill(6): row
                                      for row in _cms_rows(CMS_PROVIDER_DATASET_ID) if row.get("State") == "NV"}
            except (requests.RequestException, ValueError, KeyError) as exc:
                self.cms_error = type(exc).__name__
        return self.provider_rows or {}

    def citations(self):
        if self.deficiencies is None and self.inspection_error is None:
            try:
                by_ccn = {}
                for row in _cms_rows(CMS_INSPECTION_DATASET_ID):
                    if row.get("State") == "NV":
                        by_ccn.setdefault(str(row.get("CMS Certification Number (CCN)", "")).zfill(6), []).append(row)
                self.deficiencies = by_ccn
            except (requests.RequestException, ValueError, KeyError) as exc:
                self.inspection_error = type(exc).__name__
        return self.deficiencies or {}


def _base(topic, source, url, context):
    return {"topic": topic, "source": source, "source_url": url, "observed_at": context.now.isoformat(),
            "status": "UNKNOWN", "identity_verified": False, "data": {}}


def cms_observation(facility: dict, topic: str, context: ResearchCollectionContext) -> dict:
    dataset = CMS_INSPECTION_DATASET_ID if topic == "official_complaints" else CMS_PROVIDER_DATASET_ID
    result = _base(topic, "CMS / Medicare", f"{CMS_ROOT}/dataset/{dataset}", context)
    ccn = str(facility.get("cms_ccn") or "").strip()
    if not ccn.isdigit() or len(ccn) > 6:
        non_cms_type = str(facility.get("canonical_type") or "").upper() in {"ASSISTED_LIVING", "MEMORY_CARE", "INDEPENDENT_LIVING", "PERSONAL_CARE_AGENCY"}
        return {**result, "status": "NOT_APPLICABLE" if topic == "cms_quality" and non_cms_type else "UNKNOWN",
                "limitation": "No CMS CCN is available; CMS does not establish assisted-living quality or complaint history."}
    ccn = ccn.zfill(6)
    provider = context.providers().get(ccn)
    if not provider:
        return {**result, "status": "SOURCE_FAILED" if context.cms_error else "IDENTITY_UNRESOLVED",
                "limitation": "CMS provider identity could not be verified in the current dataset."}
    result["identity_verified"] = True
    if topic == "cms_quality":
        fields = {"overall_rating": "Overall Rating", "inspection_rating": "Health Inspection Rating",
                  "staffing_rating": "Staffing Rating", "quality_rating": "QM Rating",
                  "special_focus_status": "Special Focus Status", "abuse_icon": "Abuse Icon",
                  "nursing_staff_turnover": "Total nursing staff turnover", "rn_turnover": "Registered Nurse turnover"}
        result["data"] = {key: provider.get(column) or None for key, column in fields.items()}
        result["data"].update({"cms_ccn": ccn, "processing_date": provider.get("Processing Date"), "scale": "CMS integer stars 1–5"})
        published = parse_date(provider.get("Processing Date"))
        result["status"] = "VERIFIED" if published else "PARTIAL"
        if published and not 0 <= (context.now.date() - published).days <= 62:
            result["status"] = "STALE"
        result["limitation"] = "CMS and Medicare are the same rating source. Publication date may lag collection date."
        return result
    rows = context.citations().get(ccn, [])
    if context.inspection_error:
        return {**result, "status": "SOURCE_FAILED", "limitation": "Current CMS complaint-related findings could not be retrieved."}
    start, end = complaint_window(context.now.date())
    findings, seen = [], set()
    invalid_dates = 0
    for row in rows:
        if str(row.get("Complaint Deficiency") or "").strip().upper() != "Y":
            continue
        surveyed = parse_date(row.get("Survey Date"))
        if surveyed is None:
            invalid_dates += 1
            continue
        if not start <= surveyed <= end:
            continue
        key = (surveyed.isoformat(), row.get("Deficiency Prefix"), row.get("Deficiency Tag Number"))
        if key in seen:
            continue
        seen.add(key)
        findings.append({"date": surveyed.isoformat(), "date_type": "SURVEY_DATE_NOT_COMPLAINT_RECEIPT_DATE",
                         "finding_type": "COMPLAINT_RELATED_DEFICIENCY", "tag": row.get("Deficiency Tag Number"),
                         "subject": row.get("Deficiency Description"), "severity": row.get("Scope Severity Code"),
                         "correction_status": row.get("Deficiency Corrected") or "UNKNOWN",
                         "correction_date": row.get("Correction Date") or None,
                         "source_url": f"https://www.medicare.gov/care-compare/details/nursing-home/{ccn}"})
    result["status"] = "PARTIAL"
    published = parse_date(provider.get("Processing Date"))
    if published and not 0 <= (context.now.date() - published).days <= 62:
        result["status"] = "STALE"
    result["data"] = {"window_start": start.isoformat(), "window_end": end.isoformat(), "cms_ccn": ccn,
                      "complaint_count": None, "published_finding_count": len(findings), "findings": findings,
                      "undated_complaint_related_rows": invalid_dates,
                      "processing_date": provider.get("Processing Date")}
    result["limitation"] = "CMS publishes complaint-related deficiencies, not every complaint filed. Zero published findings does not establish zero complaints. Dates shown are inspection dates."
    return result


def nevada_observation(canonical_id: str, facility: dict, topic: str, context: ResearchCollectionContext) -> dict:
    from app.services.decision_engine_evidence import _regulatory_index
    record = _regulatory_index().get(canonical_id) or {}
    url = str(record.get("source_url") or "")
    result = _base(topic, "Nevada HCQC / ALiS", url or "https://nvdpbh.aithent.com/login.aspx", context)
    parsed = urlparse(url)
    license_number = parse_qs(parsed.query).get("LicenseNumber", [""])[0]
    if parsed.hostname != "nvdpbh.aithent.com" or not license_number:
        return {**result, "status": "IDENTITY_UNRESOLVED", "limitation": "No exact Nevada license report link is available."}
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        # Do not treat login redirects, error pages or generic portal text as a checked report.
        if response.url != url or not response.content or "login.aspx" in response.url.lower():
            return {**result, "status": "ACCESS_BLOCKED", "limitation": "The exact inspection report is not publicly retrievable in this session."}
        body = response.text
        if license_number not in body or not any(term in body.lower() for term in ("inspection", "survey", "deficien")):
            return {**result, "status": "IDENTITY_UNRESOLVED", "limitation": "The retrieved page did not confirm the exact license and report content."}
        return {**result, "status": "PARTIAL", "identity_verified": True,
                "data": {"license_number": license_number, "source_document_sha256": hashlib.sha256(response.content).hexdigest(), "complaint_count": None},
                "limitation": "The official report page was retrieved. Complaint counts, findings and verified correction still require document-level extraction; no absence of complaints is asserted."}
    except requests.RequestException:
        return {**result, "status": "SOURCE_FAILED", "limitation": "The current Nevada inspection report could not be retrieved."}


def collect_topic(canonical_id: str, facility: dict, topic: str, context: ResearchCollectionContext) -> dict:
    if facility.get("synthetic_pilot") is True or canonical_id.startswith("PILOT-NV-"):
        return {**_base(topic, "PILOT", "", context), "status": "SYNTHETIC_PILOT_NOT_PUBLIC_RESEARCH"}
    if topic == "cms_quality" or (topic == "official_complaints" and str(facility.get("cms_ccn") or "").isdigit()):
        return cms_observation(facility, topic, context)
    if topic in {"official_complaints", "regulatory_history"}:
        return nevada_observation(canonical_id, facility, topic, context)
    sources = {"google_reviews": ("Google Maps", "https://developers.google.com/maps/documentation/places/web-service/policies", "API_AND_ATTRIBUTION_REQUIRED"),
               "independent_ratings": ("U.S. News / Newsweek", "https://health.usnews.com/best-senior-living", "REDISTRIBUTION_PERMISSION_REQUIRED"),
               "accreditation": ("Joint Commission", "https://www.jointcommission.org", "AUTHORIZED_FEED_REQUIRED"),
               "staffing_operations": ("Verified provider documents", "", "DIRECT_VERIFICATION_REQUIRED")}
    source, url, blocker = sources[topic]
    return {**_base(topic, source, url, context), "status": blocker,
            "limitation": "A verified, permitted data connection is not configured. No rating or accreditation is inferred."}
