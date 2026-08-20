from __future__ import annotations

"""Extract Nevada HCQC Personal Care Agencies from the public ALiS search.

The credential code is intentionally discovered by label at runtime instead of
hard-coded. Nevada can change internal ALiS option values; the public regulatory
label is the governed identity.
"""

import argparse
import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError

from extract_nevada_hcqc_alis import (
    BUSINESS_UNIT,
    GRID_TARGET,
    LICENSE_TYPE,
    SEARCH_TARGET,
    PageParser,
    build_opener,
    CookieJar,
    HTTPCookieProcessor,
    detail_urls,
    parse_page,
    request,
    result_table,
    split_nv_address,
)

HFF_SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HFF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
PCA_LABEL = "AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME"
HEALTH_FACILITIES_VALUES = ("HFF", "HHF")


def _find_option(parser: PageParser, needle: str) -> tuple[str, str] | None:
    target = needle.strip().upper()
    for select in parser.selects:
        for value, label in select.options:
            if label.strip().upper() == target:
                return value, label
    return None


def _hff_postback(opener, parser: PageParser, target: str, argument: str, license_type: str, business_value: str) -> PageParser:
    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = target
    payload["__EVENTARGUMENT"] = argument
    payload[BUSINESS_UNIT] = business_value
    payload[LICENSE_TYPE] = license_type
    raw, _ = request(opener, HFF_SEARCH_URL, payload)
    return parse_page(raw)


def _hff_postback_retry(
    opener,
    parser: PageParser,
    target: str,
    argument: str,
    license_type: str,
    business_value: str,
    retries: int = 4,
) -> PageParser:
    last_error: HTTPError | None = None
    for attempt in range(retries):
        try:
            return _hff_postback(opener, parser, target, argument, license_type, business_value)
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 or attempt + 1 >= retries:
                raise
            time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _next_pager_argument(parser: PageParser, next_page: int) -> str | None:
    """Return only a pager argument that ALiS actually exposes on this page.

    Some ALiS result sets return HTTP 500 when a caller posts Page$N beyond the
    final GridView page. We therefore follow the server-rendered pager instead
    of guessing that every next page exists.
    """
    exact = f"Page${next_page}"
    next_token = "Page$Next"
    for anchor in parser.anchors:
        blob = " ".join(str(anchor.get(key) or "") for key in ("href", "onclick"))
        if GRID_TARGET not in blob:
            continue
        if exact in blob:
            return exact
        if next_token in blob:
            return next_token
    return None


def discover_pca_code(opener) -> tuple[str, str, str, PageParser]:
    raw, _ = request(opener, HFF_SEARCH_URL)
    parser = parse_page(raw)
    found = _find_option(parser, PCA_LABEL)
    if found:
        return found[0], found[1], "HFF", parser

    # ALiS often populates credential types only after the business unit is
    # selected. Try the public Health Facilities values, but never guess the
    # PCA credential code itself.
    for business_value in HEALTH_FACILITIES_VALUES:
        payload = dict(parser.hidden)
        payload["__EVENTTARGET"] = BUSINESS_UNIT
        payload["__EVENTARGUMENT"] = ""
        payload[BUSINESS_UNIT] = business_value
        raw, _ = request(opener, HFF_SEARCH_URL, payload)
        candidate = parse_page(raw)
        found = _find_option(candidate, PCA_LABEL)
        if found:
            return found[0], found[1], business_value, candidate
    raise RuntimeError(f"ALiS credential option not found by governed label: {PCA_LABEL}")


def collect() -> tuple[list[dict[str, str]], dict[str, object]]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    code, label, business_value, parser = discover_pca_code(opener)
    parser = _hff_postback_retry(opener, parser, LICENSE_TYPE, "", code, business_value)
    parser = _hff_postback_retry(opener, parser, SEARCH_TARGET, "", code, business_value)

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    page = 1
    page_new_record_counts: list[int] = []
    while page <= 500:
        table = result_table(parser)
        if not table:
            if page == 1:
                raise RuntimeError("PCA result table not found")
            break
        data_rows = [r for r in table[1:] if len(r) >= 14 and r[2] and r[2] != "Credential Number"]
        links = detail_urls(parser)
        added = 0
        for idx, row in enumerate(data_rows):
            credential = row[2].strip()
            if credential in seen:
                continue
            seen.add(credential)
            address = split_nv_address(row[6])
            rows.append({
                "agency_id": f"NV-PCA-{credential}",
                "agency_name": row[0] or "UNKNOWN",
                "credential_type": row[1] or label,
                "license_number": credential,
                "license_status": row[3] or "UNKNOWN",
                "expiration_date": row[4] or "UNKNOWN",
                "disciplinary_action": row[5] or "UNKNOWN",
                **address,
                "phone": row[7] or "UNKNOWN",
                "first_issue_date": row[8] or "UNKNOWN",
                "administrator": row[9] or "UNKNOWN",
                "administrator_role": row[10] or "UNKNOWN",
                "detail_url": links[idx] if idx < len(links) else "UNKNOWN",
                "source_url": HFF_SEARCH_URL,
                "source_authority": "Nevada HCQC / ALiS",
                "service_class": "NON_MEDICAL_PERSONAL_CARE_ADL",
                "serves_las_vegas_valley": "UNKNOWN",
                "bathing_assistance": "UNKNOWN",
                "dressing_assistance": "UNKNOWN",
                "transfer_assistance": "UNKNOWN",
                "minimum_visit_minutes": "UNKNOWN",
                "minimum_billable_hours": "UNKNOWN",
                "hourly_rate": "UNKNOWN",
                "employment_model": "UNKNOWN",
                "liability_insurance_verified": "UNKNOWN",
                "workers_comp_verified": "UNKNOWN",
                "background_check_verified": "UNKNOWN",
                "fixed_caregiver_possible": "UNKNOWN",
                "languages": "[]",
                "availability_status": "UNKNOWN",
            })
            added += 1
        page_new_record_counts.append(added)
        if not data_rows or added == 0:
            break

        next_page = page + 1
        pager_argument = _next_pager_argument(parser, next_page)
        if pager_argument is None:
            break
        parser = _hff_postback_retry(opener, parser, GRID_TARGET, pager_argument, code, business_value)
        page = next_page

    report = {
        "credential_label": label,
        "credential_code_discovered": code,
        "business_unit_value": business_value,
        "records": len(rows),
        "active_records": sum(1 for r in rows if str(r["license_status"]).lower() == "active"),
        "las_vegas_address_records": sum(1 for r in rows if str(r.get("city") or "").upper() in {"LAS VEGAS", "NORTH LAS VEGAS", "HENDERSON"}),
        "pages_collected": len(page_new_record_counts),
        "page_new_record_counts": page_new_record_counts,
        "policy": "HCQC/ALiS establishes license identity/status only. Service area, pricing, minimum hours, employment model, languages, availability and facility partnerships remain UNKNOWN until separately verified.",
    }
    return rows, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/hcqc_personal_care_agencies.csv")
    ap.add_argument("--report", default="reports/NEVADA_HCQC_PERSONAL_CARE_AGENCIES.json")
    args = ap.parse_args()
    rows, report = collect()
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["agency_name", "license_number", "license_status"]
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    rp = Path(args.report); rp.parent.mkdir(parents=True, exist_ok=True); rp.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not rows:
        raise SystemExit("No Personal Care Agency records extracted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
