from __future__ import annotations

import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.request
import argparse
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.source_lifecycle_service import load_registry, record_import_success, render_status_report, save_registry
from scripts.build_nevada_canonical_universe import build_universe, render_report, DEFAULT_CMS_SOURCE


REGISTRY_PATH = REPO_ROOT / "database" / "source_lifecycle_registry.json"
STATUS_REPORT_PATH = REPO_ROOT / "reports" / "SOURCE_LIFECYCLE_STATUS.md"
OUTPUT_CANONICAL = REPO_ROOT / "database" / "nevada_facility_universe_canonical.json"
OUTPUT_NEVADA_REPORT_JSON = REPO_ROOT / "reports" / "NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.json"
OUTPUT_NEVADA_REPORT_MD = REPO_ROOT / "reports" / "NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"
OUTPUT_INTEGRATION_JSON = REPO_ROOT / "reports" / "NEVADA_SOURCE_INTEGRATION_REPORT.json"
OUTPUT_INTEGRATION_MD = REPO_ROOT / "reports" / "NEVADA_SOURCE_INTEGRATION_REPORT.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrate governed Nevada authoritative sources into the canonical universe build.")
    parser.add_argument("--skip-build", action="store_true", help="Skip the heavy NPPES download/rebuild and finalize from current Nevada artifacts.")
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _latest_nppes_monthly_url() -> str:
    page = "https://download.cms.gov/nppes/NPI_Files.html"
    req = urllib.request.Request(page, headers={"User-Agent": "OPTIME-SourceIntegration/1.0"})
    with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
        html = response.read().decode("utf-8", "replace")
    match = re.search(r'href=["\'](\./NPPES_Data_Dissemination_[^"\']+?\.zip)["\']', html, flags=re.I)
    if not match:
        raise RuntimeError("No governed NPPES monthly dissemination link found")
    return urllib.request.urljoin(page, match.group(1))


def _download_nppes_zip(url: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    out = Path(path)
    req = urllib.request.Request(url, headers={"User-Agent": "OPTIME-SourceIntegration/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=ssl.create_default_context()) as response, out.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    return out


def _nv_source_record(registry: Dict[str, Any], source_id: str) -> Dict[str, Any]:
    for record in registry.get("records") or []:
        if record.get("source_id") == source_id:
            return record
    raise KeyError(source_id)


def _integration_plan(registry_record: Dict[str, Any]) -> Dict[str, Any]:
    source_id = str(registry_record.get("source_id") or "")
    name = str(registry_record.get("source_name") or "")
    lifecycle = str(registry_record.get("lifecycle_status") or "")
    blocker = str(registry_record.get("blocking_issue") or "")
    facility_types = list(registry_record.get("facility_types_covered") or [])

    if source_id == "SRC-NV-CMS-4PQ5-N9PY":
        return {
            "source_id": source_id,
            "source_name": name,
            "current_lifecycle_status": lifecycle,
            "exact_blocking_reason": "None; already integrated",
            "can_it_be_solved": "YES",
            "exactly_how": "No change required; continue using existing CMS CSV connector.",
            "estimated_facilities_gained": 0,
            "facility_categories_added": ["Skilled Nursing Facility", "Nursing Facility"],
            "expected_overlap_with_cms": "Source is CMS baseline",
            "expected_new_canonical_facilities": 0,
            "required_connector": "Existing CMS CSV reader",
            "required_parser": "Existing cms_rows() parser",
            "required_normalization": "Existing CMS address/phone/zip normalization",
            "required_validation": "Existing Nevada canonical validation",
            "connector_gap_analysis": "CSV only",
            "integrated": True,
        }
    if source_id == "SRC-NV-HCQC-LICENSING":
        return {
            "source_id": source_id,
            "source_name": name,
            "current_lifecycle_status": lifecycle,
            "exact_blocking_reason": blocker,
            "can_it_be_solved": "NO",
            "exactly_how": "Cannot be solved safely in this sprint because the official endpoint loops on redirect and no machine-readable export is exposed.",
            "estimated_facilities_gained": None,
            "facility_categories_added": facility_types,
            "expected_overlap_with_cms": "High overlap for skilled nursing; unknown overlap for assisted living and other state categories",
            "expected_new_canonical_facilities": None,
            "required_connector": "Official licensing export connector",
            "required_parser": "Nevada HCQC machine-readable export parser",
            "required_normalization": "Facility-name, address, phone, and license-ID normalization",
            "required_validation": "License ID, status, facility-type, and duplicate-merge validation",
            "connector_gap_analysis": "Redirect; No API; Manual export",
            "integrated": False,
        }
    return {
        "source_id": source_id,
        "source_name": name,
        "current_lifecycle_status": lifecycle,
        "exact_blocking_reason": blocker,
        "can_it_be_solved": "YES",
        "exactly_how": "Download the governed monthly NPPES dissemination ZIP, stream the organization file, filter Nevada practice-location rows, map residential taxonomy codes, and merge by NPI and exact normalized address/phone.",
        "estimated_facilities_gained": None,
        "facility_categories_added": ["Assisted Living", "Memory Care", "Skilled Nursing Facility", "Nursing Facility", "Continuing Care / Life Plan"],
        "expected_overlap_with_cms": "Expected overlap on skilled nursing and nursing facility records; low overlap on assisted living and memory care",
        "expected_new_canonical_facilities": None,
        "required_connector": "Streaming NPPES ZIP downloader",
        "required_parser": "npidata_pfile CSV parser with taxonomy-slot expansion",
        "required_normalization": "NPI, facility name, DBA, address, zip, phone, taxonomy normalization",
        "required_validation": "NPI-only identity checks, residential-taxonomy filter, duplicate merge and conflict audit",
        "connector_gap_analysis": "CSV only",
        "integrated": False,
    }


def _finalize_outputs(*, registry: Dict[str, Any], plans: List[Dict[str, Any]], payload: Dict[str, Any], report: Dict[str, Any], before_count: int, before_types: List[str]) -> Dict[str, Any]:
    after_records = payload.get("records") or []
    after_count = len(after_records)
    after_types = sorted({str(record.get("facility_type") or "") for record in after_records if str(record.get("facility_type") or "")})
    new_records = [record for record in after_records if str(record.get("canonical_type") or "") in {"NPI_ONLY", "COMPOSITE"}]
    overlap_with_cms = sum(1 for record in after_records if record.get("cms_certification_number") and record.get("npi"))

    cms_baseline_record = next((record for record in registry.get("records") or [] if record.get("source_id") == "SRC-NV-CMS-4PQ5-N9PY"), None)
    baseline_before_count = int((cms_baseline_record or {}).get("estimated_facility_coverage") or before_count)
    baseline_before_types = ["Skilled Nursing Facility"] if baseline_before_count <= after_count else before_types

    for record in registry.get("records") or []:
        if record.get("source_id") == "SRC-NV-NPPES-REGISTRY":
            record_import_success(registry, "SRC-NV-NPPES-REGISTRY", imported_at=payload.get("generated_at_utc") or report.get("generated_at_utc"))
            record["reason"] = "Integrated into Nevada canonical universe via streaming NPPES dissemination connector"
            record["policy_status"] = "AUTO_INTEGRATED"
            record["next_action"] = "Continue scheduled refresh"
            record["estimated_facility_coverage"] = after_count
        elif record.get("source_id") == "SRC-NV-HCQC-LICENSING":
            record["next_action"] = "Remain blocked until a machine-readable official export or stable connector is available"
    save_registry(registry, REGISTRY_PATH)
    STATUS_REPORT_PATH.write_text(render_status_report(load_registry(REGISTRY_PATH)), encoding="utf-8")

    for plan in plans:
        if plan["source_id"] == "SRC-NV-NPPES-REGISTRY":
            plan["estimated_facilities_gained"] = after_count - before_count
            plan["expected_new_canonical_facilities"] = len(new_records)
            plan["expected_overlap_with_cms"] = overlap_with_cms
            plan["integrated"] = True
            plan["current_lifecycle_status"] = "INTEGRATED"

    integration_report = {
        "generated_at_utc": payload.get("generated_at_utc") or report.get("generated_at_utc"),
        "sources_evaluated": plans,
        "sources_integrated": [plan["source_id"] for plan in plans if plan["integrated"]],
        "sources_still_blocked": [plan["source_id"] for plan in plans if not plan["integrated"]],
        "facilities_before": baseline_before_count,
        "facilities_after": after_count,
        "facility_types_before": baseline_before_types,
        "facility_types_after": after_types,
        "duplicates_removed": report.get("duplicates_merged"),
        "canonical_merges": report.get("duplicates_merged"),
        "coverage_increase": after_count - baseline_before_count,
        "remaining_gaps": {
            "records_with_nevada_license_id": report.get("records_with_nevada_license_id"),
            "records_with_npi": report.get("records_with_npi"),
            "media_pilot_gate": report.get("media_pilot_gate"),
        },
    }
    _write_json(OUTPUT_INTEGRATION_JSON, integration_report)

    lines: List[str] = []
    lines.append("# Nevada Source Integration Report")
    lines.append("")
    lines.append(f"Generated: `{integration_report['generated_at_utc']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Sources integrated: **{len(integration_report['sources_integrated'])}**")
    lines.append(f"- Sources still blocked: **{len(integration_report['sources_still_blocked'])}**")
    lines.append(f"- Facilities before: **{baseline_before_count}**")
    lines.append(f"- Facilities after: **{after_count}**")
    lines.append(f"- Coverage increase: **{after_count - baseline_before_count}**")
    lines.append(f"- Duplicates removed / canonical merges: **{report.get('duplicates_merged')}**")
    lines.append("")
    lines.append("## Source Decisions")
    lines.append("")
    lines.append("| Source | Lifecycle | Blocking reason | Solvable | Connector gap | Facilities gained | Categories added | Expected overlap with CMS | Expected new canonical facilities | Required connector | Required parser | Required normalization | Required validation |")
    lines.append("| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |")
    for plan in plans:
        categories = ", ".join(plan.get("facility_categories_added") or [])
        lines.append(
            f"| {plan['source_name']} | {plan['current_lifecycle_status']} | {plan['exact_blocking_reason']} | {plan['can_it_be_solved']} | {plan['connector_gap_analysis']} | {'' if plan['estimated_facilities_gained'] is None else plan['estimated_facilities_gained']} | {categories} | {plan['expected_overlap_with_cms']} | {'' if plan['expected_new_canonical_facilities'] is None else plan['expected_new_canonical_facilities']} | {plan['required_connector']} | {plan['required_parser']} | {plan['required_normalization']} | {plan['required_validation']} |"
        )
    lines.append("")
    lines.append("## Facility Types")
    lines.append("")
    lines.append(f"- Before: {', '.join(baseline_before_types)}")
    lines.append(f"- After: {', '.join(after_types)}")
    lines.append("")
    lines.append("## Remaining Gaps")
    lines.append("")
    lines.append(f"- Records with Nevada license ID: **{report.get('records_with_nevada_license_id')}**")
    lines.append(f"- Records with NPI: **{report.get('records_with_npi')}**")
    lines.append(f"- Media pilot gate status: **{report.get('media_pilot_gate', {}).get('status')}**")
    OUTPUT_INTEGRATION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = {
        "facilities_before": baseline_before_count,
        "facilities_after": after_count,
        "sources_integrated": integration_report["sources_integrated"],
        "sources_still_blocked": integration_report["sources_still_blocked"],
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    args = parse_args()
    registry = load_registry(REGISTRY_PATH)
    nv_records = [record for record in registry.get("records") or [] if record.get("state") == "NV"]
    plans = [_integration_plan(record) for record in nv_records]

    before_payload = _read_json(OUTPUT_CANONICAL)
    before_records = before_payload.get("records") or []
    before_count = len(before_records)
    before_types = sorted({str(record.get("facility_type") or "") for record in before_records if str(record.get("facility_type") or "")})

    if args.skip_build:
        payload = _read_json(OUTPUT_CANONICAL)
        report = _read_json(OUTPUT_NEVADA_REPORT_JSON)
        _finalize_outputs(registry=registry, plans=plans, payload=payload, report=report, before_count=before_count, before_types=before_types)
        return 0

    nppes_plan = next(plan for plan in plans if plan["source_id"] == "SRC-NV-NPPES-REGISTRY")
    nppes_temp = _download_nppes_zip(_latest_nppes_monthly_url())
    started = time.perf_counter()
    try:
        retrieved_at = nppes_plan.get("current_retrieved_at") or registry.get("generated_at_utc") or before_payload.get("generated_at_utc")
        payload, report = build_universe(DEFAULT_CMS_SOURCE, None, nppes_temp, str(retrieved_at))
    finally:
        try:
            nppes_temp.unlink()
        except OSError:
            pass

    report.setdefault("processing_time_seconds", round(time.perf_counter() - started, 3))
    report.setdefault("peak_memory_mib", None)
    report.setdefault("peak_memory_measurement", "not_measured_in_integration_runner")

    OUTPUT_CANONICAL.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_NEVADA_REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_NEVADA_REPORT_MD.write_text(render_report(report), encoding="utf-8")

    _finalize_outputs(registry=registry, plans=plans, payload=payload, report=report, before_count=before_count, before_types=before_types)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())