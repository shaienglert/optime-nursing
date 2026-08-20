from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


BLOCKED_PRIMARY_DOMAINS = {
    "cms.gov",
    "medicare.gov",
    "dpbh.nv.gov",
    "nvdpbh.aithent.com",
    "health.nv.gov",
    "myhealthfacilitylicense.nv.gov",
    "carecompare.gov",
}
BLOCKED_THIRD_PARTY_DOMAINS = {
    "aplaceformom.com",
    "caring.com",
    "seniorly.com",
    "yelp.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "yellowpages.com",
    "bbb.org",
    "mapquest.com",
}


def _domain(url: object) -> str:
    text = str(url or "").strip()
    if not text.startswith(("http://", "https://")):
        return ""
    return urlparse(text).netloc.lower().split(":", 1)[0]


def _matches(domain: str, blocked: set[str]) -> bool:
    return any(domain == item or domain.endswith("." + item) for item in blocked)


def sanitize_record(row: dict) -> dict:
    out = dict(row)
    domain = _domain(out.get("primary_source_url"))
    invalid_reason = None
    if domain and _matches(domain, BLOCKED_PRIMARY_DOMAINS):
        invalid_reason = "REGULATORY_OR_GOVERNMENT_SOURCE_IS_NOT_AGENCY_PRIMARY_SOURCE"
    elif domain and _matches(domain, BLOCKED_THIRD_PARTY_DOMAINS):
        invalid_reason = "THIRD_PARTY_DIRECTORY_IS_NOT_AGENCY_PRIMARY_SOURCE"

    if invalid_reason:
        out["rejected_candidate_url"] = out.get("primary_source_url")
        out["rejected_candidate_domain"] = domain
        out["rejected_candidate_reason"] = invalid_reason
        out["primary_source_url"] = "UNKNOWN"
        out["identity_verified"] = False
        out["research_status"] = "CANDIDATE_REJECTED_NOT_AGENCY_PRIMARY_SOURCE"
        for field in (
            "bathing_assistance", "dressing_assistance", "transfer_assistance",
            "medication_reminders", "meal_preparation", "light_housekeeping",
            "minimum_billable_hours", "minimum_visit_minutes", "employment_model",
            "liability_insurance_verified", "workers_comp_verified",
            "background_check_verified", "fixed_caregiver_possible",
            "availability_status", "languages", "published_hourly_rate_candidates",
            "hourly_rate_for_requested_schedule", "serves_las_vegas_valley",
        ):
            if field in out:
                out[field] = "UNKNOWN" if field != "languages" else []
    return out


def sanitize_payload(payload: dict) -> dict:
    records = [sanitize_record(row) for row in payload.get("records") or []]
    payload = dict(payload)
    payload["records"] = records
    payload["identity_verified"] = sum(1 for row in records if row.get("identity_verified") is True)
    payload["source_not_found"] = sum(1 for row in records if row.get("research_status") == "SOURCE_NOT_FOUND")
    payload["candidate_rejected_not_primary"] = sum(
        1 for row in records if row.get("research_status") == "CANDIDATE_REJECTED_NOT_AGENCY_PRIMARY_SOURCE"
    )
    payload["sanitization_policy"] = (
        "Government/regulatory pages and third-party directories can support discovery or regulatory evidence, "
        "but can never be promoted to agency primary operational evidence."
    )
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH.json")
    args = ap.parse_args()
    src = Path(args.input)
    payload = json.loads(src.read_text(encoding="utf-8"))
    cleaned = sanitize_payload(payload)
    Path(args.output).write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "attempted": cleaned.get("attempted", 0),
        "identity_verified": cleaned.get("identity_verified", 0),
        "candidate_rejected_not_primary": cleaned.get("candidate_rejected_not_primary", 0),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
