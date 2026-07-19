import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PATH = ROOT / "database" / "florida_senior_living_inventory.json"
MANIFEST_PATH = ROOT / "reports" / "canonical_facility_universe_manifest.json"
DISCOVERY_REPORT_PATH = ROOT / "reports" / "discovery_report.md"
EXEC_DASHBOARD_PATH = ROOT / "reports" / "executive_dashboard.md"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return re.sub(r"\s+", " ", text)


def _truthy(value) -> bool:
    return value is not None and str(value).strip() != ""


def _error(errors, message):
    errors.append(message)


def validate() -> int:
    errors = []

    canonical = _load_json(CANONICAL_PATH)
    manifest = _load_json(MANIFEST_PATH)
    records = canonical.get("records", [])

    now = datetime.now(timezone.utc)

    # totals mismatch: metadata totals and expected totals must equal observed totals
    observed_record_count = len(records)
    meta_record_count = canonical.get("record_count")
    expected_record_count = manifest["validation_expectations"]["record_count"]
    if observed_record_count != meta_record_count:
        _error(
            errors,
            f"Totals mismatch: canonical record_count metadata={meta_record_count} observed={observed_record_count}",
        )
    if observed_record_count != expected_record_count:
        _error(
            errors,
            f"Totals mismatch: expected record_count={expected_record_count} observed={observed_record_count}",
        )

    counties = sorted({_norm(r.get("county")) for r in records if _norm(r.get("county"))})
    observed_counties_covered = len(counties)
    expected_counties_covered = manifest["validation_expectations"]["counties_covered"]
    expected_counties_total = manifest["validation_expectations"]["counties_total"]

    if canonical.get("counties_covered") != observed_counties_covered:
        _error(
            errors,
            "Coverage disagreement: counties_covered metadata does not match observed unique counties",
        )
    if observed_counties_covered != expected_counties_covered:
        _error(
            errors,
            f"Coverage disagreement: expected counties_covered={expected_counties_covered} observed={observed_counties_covered}",
        )
    if canonical.get("counties_total") != expected_counties_total:
        _error(
            errors,
            f"Coverage disagreement: canonical counties_total={canonical.get('counties_total')} expected={expected_counties_total}",
        )

    expected_missing = sorted(_norm(c) for c in manifest["validation_expectations"]["counties_missing"])
    meta_missing = sorted(_norm(c) for c in canonical.get("counties_missing", []))
    calc_missing_count = expected_counties_total - observed_counties_covered
    if len(meta_missing) != calc_missing_count:
        _error(
            errors,
            f"Totals mismatch: counties_missing metadata length={len(meta_missing)} but computed missing={calc_missing_count}",
        )
    if meta_missing != expected_missing:
        _error(
            errors,
            f"Coverage disagreement: counties_missing metadata={meta_missing} expected={expected_missing}",
        )

    # canonical ID duplicates and conflicting merges on authoritative IDs
    ccn_to_rows = defaultdict(list)
    license_to_rows = defaultdict(list)
    for row in records:
        name = _norm(row.get("community_name"))
        ccn = _norm(row.get("cms_certification_number"))
        lic = _norm(row.get("state_license_number"))
        if ccn:
            ccn_to_rows[ccn].append(name)
        if lic:
            license_to_rows[lic].append(name)

    duplicate_ccn = [k for k, v in ccn_to_rows.items() if len(v) > 1]
    duplicate_lic = [k for k, v in license_to_rows.items() if len(v) > 1]
    if duplicate_ccn or duplicate_lic:
        _error(
            errors,
            f"Canonical ID duplicates detected: duplicate_ccn={len(duplicate_ccn)} duplicate_license={len(duplicate_lic)}",
        )

    conflicting_ccn = [k for k, v in ccn_to_rows.items() if len(set(v)) > 1]
    conflicting_lic = [k for k, v in license_to_rows.items() if len(set(v)) > 1]
    if conflicting_ccn or conflicting_lic:
        _error(
            errors,
            f"Conflicting ID merges detected: conflicting_ccn={len(conflicting_ccn)} conflicting_license={len(conflicting_lic)}",
        )

    # provenance gaps
    required_fields = manifest["validation_expectations"]["provenance_required_fields"]
    missing_provenance = 0
    for row in records:
        for field in required_fields:
            value = row.get(field)
            if isinstance(value, list):
                if len(value) == 0:
                    missing_provenance += 1
                    break
            elif not _truthy(value):
                missing_provenance += 1
                break

    if missing_provenance > 0:
        _error(errors, f"Provenance gaps detected: {missing_provenance} records missing required provenance fields")

    # ensure active reports do not present 3/67 as current truth
    discovery_text = DISCOVERY_REPORT_PATH.read_text(encoding="utf-8")
    exec_text = EXEC_DASHBOARD_PATH.read_text(encoding="utf-8")

    forbidden_current_truth_pattern = re.compile(r"^\s*-\s*Coverage:\s*\*\*3/67 counties\*\*\s*$", re.MULTILINE)
    if forbidden_current_truth_pattern.search(discovery_text):
        _error(errors, "Coverage disagreement: discovery_report.md still presents 3/67 as current truth")
    if forbidden_current_truth_pattern.search(exec_text):
        _error(errors, "Coverage disagreement: executive_dashboard.md still presents 3/67 as current truth")

    if "LEGACY_REGIONAL_SNAPSHOT" not in discovery_text:
        _error(errors, "Coverage disagreement: discovery_report.md missing explicit legacy scope classification")
    if "Canonical Statewide Coverage: **64/67 counties**" not in exec_text:
        _error(errors, "Coverage disagreement: executive_dashboard.md missing canonical statewide coverage line")

    # check key manifest expectations
    cms_linked = sum(1 for r in records if _truthy(r.get("cms_certification_number")))
    if cms_linked != manifest["validation_expectations"]["cms_linked"]:
        _error(
            errors,
            f"Totals mismatch: cms_linked expected={manifest['validation_expectations']['cms_linked']} observed={cms_linked}",
        )

    # official-source verification
    cms_official_count = 0
    medicare_official_count = 0
    florida_official_marker_count = 0
    cms_linked_without_official_marker = 0
    for row in records:
        refs = " | ".join(row.get("source_refs", []) or [])
        urls = " | ".join(row.get("source_urls", []) or [])
        blob = f"{refs} | {urls}".lower()
        has_cms_official = ("cms provider information" in blob) or ("data.cms.gov" in blob)
        has_medicare_official = ("medicare care compare" in blob) or ("medicare.gov" in blob)
        has_florida_official = ("florida healthfinder" in blob) or ("ahca" in blob) or ("flhealthsource" in blob)

        if has_cms_official:
            cms_official_count += 1
        if has_medicare_official:
            medicare_official_count += 1
        if has_florida_official:
            florida_official_marker_count += 1

        if _truthy(row.get("cms_certification_number")) and not (has_cms_official or has_medicare_official):
            cms_linked_without_official_marker += 1

    expected_cms_linked_missing_max = manifest["validation_expectations"]["official_source"][
        "cms_linked_without_official_marker_max"
    ]
    if cms_linked_without_official_marker > expected_cms_linked_missing_max:
        _error(
            errors,
            "Official-source verification mismatch: "
            f"cms_linked_without_official_marker={cms_linked_without_official_marker} exceeds max={expected_cms_linked_missing_max}",
        )

    # freshness validation
    generated_at_raw = canonical.get("generated_at_utc")
    try:
        generated_at = datetime.fromisoformat(str(generated_at_raw).replace("Z", "+00:00"))
        generated_age_days = (now - generated_at).total_seconds() / 86400.0
    except Exception:
        generated_age_days = None
        _error(errors, f"Freshness violation: invalid generated_at_utc={generated_at_raw}")

    missing_last_source_date = 0
    parsed_last_source_dates = []
    for row in records:
        raw = str(row.get("last_source_date") or "").strip()
        if not raw:
            missing_last_source_date += 1
            continue
        try:
            parsed_last_source_dates.append(datetime.fromisoformat(f"{raw}T00:00:00+00:00"))
        except Exception:
            missing_last_source_date += 1

    presence_ratio = 0.0
    if records:
        presence_ratio = (len(records) - missing_last_source_date) / len(records)

    oldest_source_age_days = None
    if parsed_last_source_dates:
        oldest_source_age_days = (now - min(parsed_last_source_dates)).total_seconds() / 86400.0

    freshness_expectations = manifest["validation_expectations"]["freshness"]
    if generated_age_days is not None and generated_age_days > freshness_expectations["generated_age_days_max"]:
        _error(
            errors,
            "Freshness violation: "
            f"generated_age_days={generated_age_days:.2f} exceeds max={freshness_expectations['generated_age_days_max']}",
        )
    if presence_ratio < freshness_expectations["last_source_date_presence_ratio_min"]:
        _error(
            errors,
            "Freshness violation: "
            f"last_source_date_presence_ratio={presence_ratio:.4f} below min={freshness_expectations['last_source_date_presence_ratio_min']}",
        )
    if oldest_source_age_days is not None and oldest_source_age_days > freshness_expectations["last_source_oldest_age_days_max"]:
        _error(
            errors,
            "Freshness violation: "
            f"oldest_source_age_days={oldest_source_age_days:.2f} exceeds max={freshness_expectations['last_source_oldest_age_days_max']}",
        )

    # runtime wiring audit for legacy retirement
    forbidden_runtime_refs = manifest["validation_expectations"].get("runtime_must_not_reference_legacy_sources", [])
    runtime_audit_paths = manifest["validation_expectations"].get("runtime_audit_paths", [])
    runtime_violations = []
    for relative_path in runtime_audit_paths:
        scan_root = ROOT / relative_path
        if not scan_root.exists():
            continue
        for dirpath, _, filenames in os.walk(scan_root):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"}:
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    continue
                normalized_text = text.replace("\\", "/")
                for forbidden in forbidden_runtime_refs:
                    if forbidden in normalized_text:
                        runtime_violations.append(f"{file_path.relative_to(ROOT)} -> {forbidden}")

    if runtime_violations:
        _error(
            errors,
            "Legacy-source runtime reference violations: " + "; ".join(runtime_violations[:20]),
        )

    if errors:
        print("PHASE1_CANONICAL_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("PHASE1_CANONICAL_VALIDATION=PASS")
    print(f"CANONICAL_TOTAL={observed_record_count}")
    print(f"CANONICAL_COVERAGE={observed_counties_covered}/{expected_counties_total}")
    print(f"CANONICAL_CMS_LINKED={cms_linked}")
    print("CANONICAL_ID_DUPLICATES=0")
    print("CONFLICTING_ID_MERGES=0")
    print("PROVENANCE_GAPS=0")
    print("OFFICIAL_SOURCE_VERIFICATION=PASS")
    print("FRESHNESS_VERIFICATION=PASS")
    print("LEGACY_RETIREMENT_RUNTIME_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
