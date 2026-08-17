from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
BASE_URL = "https://nvdpbh.aithent.com"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"
BUSINESS_UNIT = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$ddlBusinessUnit"
LICENSE_TYPE = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$cmbLicenseType"
SEARCH_TARGET = "ctl00$ContentPlaceHolder1$CommonLinkButton1"
GRID_TARGET = "ctl00$ContentPlaceHolder1$ucLicenseeSearchResult$ResultsGrid"
LICENSE_TYPES = {
    "AGC": "RESIDENTIAL FACILITY FOR GROUPS",
    "SNF": "FACILITY FOR SKILLED NURSING",
    "SFD": "SKILLED NURSING FACILITY DISTINCT PART OF HOSPITAL",
}

RESULT_HEADERS = [
    "Name", "Credential Type", "Credential Number", "Status", "Expiration Date",
    "Disciplinary Action – If Yes Click on View Detail", "Address", "Phone#",
    "First Issue Date", "Primary Contact Name", "Primary Contact Role", "Bed Count",
    "Action", "Federal Provider #",
]

@dataclass
class SelectInfo:
    name: str
    options: list[tuple[str, str]]

class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden: dict[str, str] = {}
        self.selects: list[SelectInfo] = []
        self.anchors: list[dict[str, str]] = []
        self.tables: list[list[list[str]]] = []
        self._select_name: str | None = None
        self._options: list[tuple[str, str]] = []
        self._option_value = ""
        self._option_text: list[str] = []
        self._anchor_attrs: dict[str, str] | None = None
        self._anchor_text: list[str] = []
        self._table_depth = 0
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "input" and a.get("type", "").lower() == "hidden" and a.get("name"):
            self.hidden[a["name"]] = a.get("value", "")
        elif tag == "a":
            self._anchor_attrs = a
            self._anchor_text = []
        elif tag == "select":
            self._select_name = a.get("name") or a.get("id")
            self._options = []
        elif tag == "option" and self._select_name:
            self._option_value = a.get("value", "")
            self._option_text = []
        elif tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table = []
        elif tag == "tr" and self._table is not None and self._table_depth == 1:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None and self._table_depth == 1:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._select_name:
            self._option_text.append(data)
        if self._anchor_attrs is not None:
            self._anchor_text.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._select_name:
            text = re.sub(r"\s+", " ", html.unescape("".join(self._option_text))).strip()
            self._options.append((self._option_value, text))
            self._option_text = []
        elif tag == "select" and self._select_name:
            self.selects.append(SelectInfo(self._select_name, self._options))
            self._select_name = None
            self._options = []
        elif tag == "a" and self._anchor_attrs is not None:
            item = dict(self._anchor_attrs)
            item["text"] = re.sub(r"\s+", " ", html.unescape("".join(self._anchor_text))).strip()
            self.anchors.append(item)
            self._anchor_attrs = None
            self._anchor_text = []
        elif tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", html.unescape("".join(self._cell))).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None and self._table_depth == 1:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table":
            if self._table_depth == 1 and self._table is not None:
                if self._table:
                    self.tables.append(self._table)
                self._table = None
            self._table_depth = max(0, self._table_depth - 1)


def parse_page(raw: bytes) -> PageParser:
    parser = PageParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser


def request(opener, url: str, data: dict[str, str] | None = None) -> tuple[bytes, dict[str, str]]:
    encoded = urlencode(data).encode("utf-8") if data is not None else None
    req = Request(
        url,
        data=encoded,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Referer": SEARCH_URL},
        method="POST" if data is not None else "GET",
    )
    with opener.open(req, timeout=90) as response:
        return response.read(), dict(response.headers.items())


def postback(opener, parser: PageParser, target: str, argument: str, license_type: str) -> tuple[PageParser, bytes]:
    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = target
    payload["__EVENTARGUMENT"] = argument
    payload[BUSINESS_UNIT] = "HHF"
    payload[LICENSE_TYPE] = license_type
    raw, _headers = request(opener, SEARCH_URL, payload)
    return parse_page(raw), raw


def result_table(parser: PageParser) -> list[list[str]]:
    for table in reversed(parser.tables):
        if not table:
            continue
        header = table[0]
        if len(header) >= 10 and header[:5] == RESULT_HEADERS[:5] and "Credential Number" in header:
            return table
    return []


def detail_urls(parser: PageParser) -> list[str]:
    urls: list[str] = []
    for anchor in parser.anchors:
        if anchor.get("text", "").strip().lower() != "view detail":
            continue
        onclick = html.unescape(anchor.get("onclick", ""))
        match = re.search(r"window\.open\('([^']+SODPublicView\.aspx[^']*)'", onclick, flags=re.I)
        if match:
            urls.append(urljoin(BASE_URL, match.group(1)))
    return urls


def split_nv_address(value: str) -> dict[str, str]:
    text = re.sub(r"\s+", " ", value or "").strip()
    match = re.match(r"^(?P<street>.+?)\s+(?P<city>[A-Z][A-Z .'-]+),\s*NV\s+(?P<zip>\d{5})(?:-\d{4})?$", text, flags=re.I)
    if not match:
        return {"address": text, "city": "UNKNOWN", "state": "NV", "zip": "UNKNOWN"}
    return {"address": match.group("street").strip(), "city": match.group("city").strip(), "state": "NV", "zip": match.group("zip")}


def normalized_label(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def extract_detail(raw: bytes, url: str) -> dict[str, Any]:
    parser = parse_page(raw)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", errors="replace")))).strip()
    pairs: dict[str, str] = {}
    for table in parser.tables:
        for row in table:
            if len(row) == 2 and row[0] and row[1]:
                key = normalized_label(row[0])
                if key and key not in pairs:
                    pairs[key] = row[1]
            elif len(row) >= 4 and len(row) % 2 == 0:
                for idx in range(0, len(row), 2):
                    if row[idx] and row[idx + 1]:
                        key = normalized_label(row[idx])
                        if key and key not in pairs:
                            pairs[key] = row[idx + 1]
    keywords = []
    lower = text.lower()
    for keyword in ("alzheimer", "dementia", "memory care"):
        if keyword in lower:
            keywords.append(keyword)
    contexts = []
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword), lower):
            contexts.append(text[max(0, match.start()-140):match.end()+220])
            if len(contexts) >= 8:
                break
    endorsement_like = any(any(token in key for token in ("endorsement", "condition", "service", "special")) and any(k in str(value).lower() for k in ("alzheimer", "dementia", "memory care")) for key, value in pairs.items())
    return {
        "detail_url": url,
        "detail_fields": pairs,
        "memory_keywords": keywords,
        "memory_contexts": contexts,
        "memory_care_official_detail_evidence": endorsement_like,
    }


def collect_type(code: str, include_details: bool, throttle: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    raw, _ = request(opener, SEARCH_URL)
    parser = parse_page(raw)
    parser, _ = postback(opener, parser, LICENSE_TYPE, "", code)
    parser, _ = postback(opener, parser, SEARCH_TARGET, "", code)

    rows: list[dict[str, Any]] = []
    seen_credentials: set[str] = set()
    page = 1
    page_counts: list[int] = []
    while page <= 500:
        table = result_table(parser)
        if not table:
            if page == 1:
                raise RuntimeError(f"{code}: result table not found")
            break
        data_rows = [row for row in table[1:] if len(row) >= 14 and row[2] and row[2] != "Credential Number"]
        links = detail_urls(parser)
        added = 0
        for idx, row in enumerate(data_rows):
            credential = row[2].strip()
            if credential in seen_credentials:
                continue
            seen_credentials.add(credential)
            address = split_nv_address(row[6])
            record: dict[str, Any] = {
                "facility_name": row[0] or "UNKNOWN",
                "license_type": code,
                "source_facility_type": row[1] or LICENSE_TYPES[code],
                "license_number": credential,
                "status": row[3] or "UNKNOWN",
                "expiration_date": row[4] or "UNKNOWN",
                "disciplinary_action": row[5] or "UNKNOWN",
                **address,
                "phone": row[7] or "UNKNOWN",
                "first_issue_date": row[8] or "UNKNOWN",
                "primary_contact_name": row[9] or "UNKNOWN",
                "primary_contact_role": row[10] or "UNKNOWN",
                "capacity": row[11] or "UNKNOWN",
                "detail_url": links[idx] if idx < len(links) else "UNKNOWN",
                "federal_provider_number": row[13] or "UNKNOWN",
                "source_url": SEARCH_URL,
                "source_authority": "Nevada HCQC / ALiS",
                "memory_care_classification": "UNKNOWN" if code == "AGC" else "NOT_APPLICABLE",
                "memory_care_evidence": [],
            }
            rows.append(record)
            added += 1
        page_counts.append(added)
        if not data_rows or added == 0:
            break
        page += 1
        try:
            parser, _ = postback(opener, parser, GRID_TARGET, f"Page${page}", code)
        except Exception:
            break
        if throttle:
            time.sleep(throttle)

    detail_failures = 0
    detail_memory_keyword_hits = 0
    detail_memory_confirmed = 0
    if include_details and code == "AGC":
        for index, record in enumerate(rows, start=1):
            url = record["detail_url"]
            if not isinstance(url, str) or not url.startswith("http"):
                continue
            try:
                raw, _ = request(opener, url)
                detail = extract_detail(raw, url)
                record["official_detail"] = detail["detail_fields"]
                record["memory_care_evidence"] = detail["memory_contexts"]
                if detail["memory_keywords"]:
                    detail_memory_keyword_hits += 1
                    record["memory_care_classification"] = "CANDIDATE_OFFICIAL_DETAIL_KEYWORD"
                if detail["memory_care_official_detail_evidence"]:
                    detail_memory_confirmed += 1
                    record["memory_care_classification"] = "CONFIRMED_OFFICIAL_DETAIL"
                if throttle:
                    time.sleep(throttle)
            except Exception as exc:
                detail_failures += 1
                record["official_detail_error"] = type(exc).__name__
    return rows, {
        "license_type": code,
        "records": len(rows),
        "pages_attempted": len(page_counts),
        "page_new_record_counts": page_counts,
        "detail_failures": detail_failures,
        "detail_memory_keyword_hits": detail_memory_keyword_hits,
        "detail_memory_confirmed": detail_memory_confirmed,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scalar_fields = [
        "facility_name", "license_number", "license_type", "source_facility_type", "status", "expiration_date",
        "disciplinary_action", "address", "city", "state", "zip", "phone", "first_issue_date",
        "primary_contact_name", "primary_contact_role", "capacity", "federal_provider_number", "detail_url",
        "source_url", "source_authority", "memory_care_classification", "memory_care_evidence", "official_detail",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scalar_fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["memory_care_evidence"] = json.dumps(row.get("memory_care_evidence", []), ensure_ascii=False)
            out["official_detail"] = json.dumps(row.get("official_detail", {}), ensure_ascii=False, sort_keys=True)
            writer.writerow(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--report", default="reports/NEVADA_HCQC_ALIS_EXTRACTION.json")
    ap.add_argument("--skip-details", action="store_true")
    ap.add_argument("--throttle", type=float, default=0.05)
    args = ap.parse_args()

    all_rows: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for code in ("AGC", "SNF", "SFD"):
        rows, report = collect_type(code, include_details=not args.skip_details, throttle=max(0.0, args.throttle))
        all_rows.extend(rows)
        reports.append(report)
        print(json.dumps(report, sort_keys=True))

    credentials = [row["license_number"] for row in all_rows]
    if len(credentials) != len(set(credentials)):
        raise SystemExit("Duplicate Nevada credential numbers remained after extraction")
    if not all_rows:
        raise SystemExit("Nevada ALiS extraction returned zero records")

    output = Path(args.output)
    write_csv(output, all_rows)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "source": "Nevada HCQC / ALiS public license search",
        "source_url": SEARCH_URL,
        "license_types": LICENSE_TYPES,
        "records_total": len(all_rows),
        "records_by_type": {item["license_type"]: item["records"] for item in reports},
        "detail_summary": reports,
        "output": str(output),
    }
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
