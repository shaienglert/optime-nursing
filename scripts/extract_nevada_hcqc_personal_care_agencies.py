from __future__ import annotations

"""Extract Nevada HCQC Personal Care Agencies from the public ALiS search.

The credential code is intentionally discovered by label at runtime instead of
hard-coded. Nevada can change internal ALiS option values; the public regulatory
label is the governed identity.
"""

import argparse
import csv
import json
from pathlib import Path

from extract_nevada_hcqc_alis import (
    BUSINESS_UNIT,
    LICENSE_TYPE,
    SEARCH_TARGET,
    SEARCH_URL,
    PageParser,
    build_opener,
    CookieJar,
    HTTPCookieProcessor,
    detail_urls,
    parse_page,
    postback,
    request,
    result_table,
    split_nv_address,
)

PCA_LABEL = "AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME"
HEALTH_FACILITIES_VALUES = ("HFF", "HHF")


def _find_option(parser: PageParser, needle: str) -> tuple[str, str] | None:
    target = needle.strip().upper()
    for select in parser.selects:
        for value, label in select.options:
            if label.strip().upper() == target:
                return value, label
    return None


def discover_pca_code(opener) -> tuple[str, str, PageParser]:
    raw, _ = request(opener, SEARCH_URL.replace("Program=HHF", "Program=HFF"))
    parser = parse_page(raw)
    found = _find_option(parser, PCA_LABEL)
    if found:
        return found[0], found[1], parser

    # ALiS may populate credential types only after the Health Facilities
    # business unit is selected. Try the known public business-unit values,
    # but never guess the credential code itself.
    for business_value in HEALTH_FACILITIES_VALUES:
        payload = dict(parser.hidden)
        payload["__EVENTTARGET"] = BUSINESS_UNIT
        payload["__EVENTARGUMENT"] = ""
        payload[BUSINESS_UNIT] = business_value
        raw, _ = request(opener, SEARCH_URL.replace("Program=HHF", "Program=HFF"), payload)
        candidate = parse_page(raw)
        found = _find_option(candidate, PCA_LABEL)
        if found:
            return found[0], found[1], candidate
    raise RuntimeError(f"ALiS credential option not found by governed label: {PCA_LABEL}")


def collect() -> tuple[list[dict[str, str]], dict[str, object]]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    code, label, parser = discover_pca_code(opener)

    # Reuse the same postback mechanics as the facility extractor. The helper
    # hard-codes the Health Facilities business unit; only the discovered PCA
    # credential code is supplied here.
    parser, _ = postback(opener, parser, LICENSE_TYPE, "", code)
    parser, _ = postback(opener, parser, SEARCH_TARGET, "", code)

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    page = 1
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
                "source_url": SEARCH_URL.replace("Program=HHF", "Program=HFF"),
                "source_authority": "Nevada HCQC / ALiS",
                "service_class": "NON_MEDICAL_PERSONAL_CARE_ADL",
            })
            added += 1
        if not data_rows or added == 0:
            break
        page += 1
        parser, _ = postback(opener, parser, "ctl00$ContentPlaceHolder1$ucLicenseeSearchResult$ResultsGrid", f"Page${page}", code)

    report = {
        "credential_label": label,
        "credential_code_discovered": code,
        "records": len(rows),
        "active_records": sum(1 for r in rows if str(r["license_status"]).lower() == "active"),
        "clark_county_records": sum(1 for r in rows if str(r.get("city") or "").upper() in {"LAS VEGAS", "NORTH LAS VEGAS", "HENDERSON"}),
        "policy": "HCQC/ALiS establishes license identity/status only. Pricing, minimum hours, employment model, languages, availability and facility partnerships remain UNKNOWN until separately verified.",
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
