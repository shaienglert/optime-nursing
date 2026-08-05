import csv
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REPORTS_ROOT = REPOSITORY_ROOT / "reports"
PROFILE_PATH = REPORTS_ROOT / "OPTIME_GOLDEN_FACILITY_PALACE_105719.json"
LEDGER_PATH = REPORTS_ROOT / "OPTIME_GOLDEN_FACILITY_EVIDENCE_LEDGER.csv"
ACTION_PATH = REPORTS_ROOT / "OPTIME_GOLDEN_FACILITY_ACTION_MATRIX.csv"
REQUEST_PATH = REPORTS_ROOT / "OPTIME_GOLDEN_FACILITY_INFORMATION_REQUEST.json"
TRACKER_PATH = REPORTS_ROOT / "OPTIME_FACILITY_REQUEST_TRACKER.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _identity_evidence(identity: dict[str, Any], audit_date: str) -> list[dict[str, Any]]:
    canonical_source = "database/florida_facility_universe_canonical.json"
    audited_source = "reports/OPTIME_GOLDEN_FACILITY_PALACE_105719.json"
    fields = [
        ("official_name", "Official name", identity.get("requested_name"), audited_source),
        ("legal_name", "Canonical CMS name", identity.get("canonical_name"), canonical_source),
        ("address", "Address", identity.get("address"), canonical_source),
        ("city", "City", identity.get("city"), canonical_source),
        ("state", "State", identity.get("state"), canonical_source),
        ("zip", "ZIP code", identity.get("zip"), canonical_source),
        ("county", "County", identity.get("county"), canonical_source),
        ("phone", "Phone", identity.get("phone"), canonical_source),
        ("cms_ccn", "CMS CCN", identity.get("cms_ccn"), canonical_source),
        ("facility_type", "Facility type", identity.get("facility_type"), canonical_source),
        ("ownership_type", "Ownership type", identity.get("ownership_type"), canonical_source),
        ("certified_beds", "Certified beds", identity.get("beds"), canonical_source),
        ("medicare_medicaid", "Medicare / Medicaid participation", identity.get("medicare_medicaid"), audited_source),
        ("state_license", "State license", identity.get("license_number"), audited_source),
        ("website", "Website", identity.get("official_website"), audited_source),
        ("coordinates", "Coordinates", identity.get("coordinates"), audited_source),
        ("npi", "NPI", identity.get("canonical_npi"), audited_source),
        ("aliases", "Aliases", identity.get("aliases"), audited_source),
    ]
    records: list[dict[str, Any]] = []
    for record_id, label, value, source in fields:
        is_unknown = value is None or str(value).upper().startswith("UNKNOWN")
        records.append(
            {
                "record_id": f"identity-{record_id}",
                "parameter_id": record_id,
                "parameter": label,
                "value": "UNKNOWN" if is_unknown else value,
                "evidence_status": "UNKNOWN" if is_unknown else "VERIFIED",
                "confidence": "UNKNOWN" if is_unknown else "HIGH",
                "source_category": "Repository canonical identity",
                "source_name": Path(source).name,
                "source_url_or_local_file": source,
                "dataset_name": "Canonical facility identity",
                "record_identifier": identity.get("cms_ccn"),
                "retrieval_date": audit_date,
                "publication_date": "",
                "evidence_quote": "No verified value in the canonical facility record." if is_unknown else f"{label}: {value}",
                "recency": "UNKNOWN" if is_unknown else "FRESH",
                "contradictory_sources": "NONE_DETECTED",
                "used_in_eligibility": "NO",
                "used_in_ranking": "NO",
                "displayed_in_ui": "YES",
            }
        )
    return records


def get_live_facility_profile(cms_ccn: str) -> dict[str, Any]:
    profile = _load_json(PROFILE_PATH)
    identity = profile["identity"]
    if str(identity.get("cms_ccn")) != str(cms_ccn):
        raise KeyError(cms_ccn)

    facts = _load_csv(LEDGER_PATH)
    actions = _load_csv(ACTION_PATH)
    request = _load_optional_json(REQUEST_PATH)
    tracker = _load_optional_json(TRACKER_PATH)
    identity_records = _identity_evidence(identity, profile["audit_date"])
    sources = sorted(
        {
            row["source_name"]
            for row in facts
            if row.get("source_name") and row["source_name"] != "Not verified"
        }
    )

    verified_count = sum(row.get("evidence_status") == "VERIFIED" for row in facts)
    unknown_count = sum(row.get("evidence_status") == "UNKNOWN" for row in facts)
    critical_unknown_count = sum(
        row.get("Priority") == "CRITICAL" and row.get("evidence_status") != "VERIFIED"
        for row in facts
    )

    return {
        "facility": {
            "canonical_facility_id": profile["canonical_facility_id"],
            "display_name": identity["requested_name"].title().replace("&", "&"),
            **identity,
        },
        "summary": {
            "fact_count": len(facts),
            "verified_fact_count": verified_count,
            "unknown_fact_count": unknown_count,
            "actionable_fact_count": len(actions),
            "critical_unknown_count": critical_unknown_count,
            "source_count": len(sources),
            "profile_completeness_percent": round((len(facts) - unknown_count) / len(facts) * 100),
            "last_updated": profile["audit_date"],
            "evidence_record_count": profile["evidence_summary"]["raw_evidence_rows"],
            "evidence_confidence": "MIXED",
        },
        "facts": facts,
        "identity_evidence": identity_records,
        "actions": actions,
        "sources": sources,
        "quality_safety": profile["quality_safety"],
        "staffing": profile["staffing"],
        "unknown_sections": profile["unknown_sections"],
        "email_request": request,
        "request_tracker": tracker,
        "safety_controls": {
            "email_send_enabled": False,
            "production_write_enabled": False,
            "ranking_write_enabled": False,
        },
    }