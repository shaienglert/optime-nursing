from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"
BUSINESS_UNIT = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$ddlBusinessUnit"
LICENSE_TYPE = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$cmbLicenseType"
SEARCH_TARGET = "ctl00$ContentPlaceHolder1$CommonLinkButton1"
EXPORT_TARGET = "ctl00$ContentPlaceHolder1$btnGenerateExcel"

@dataclass
class SelectInfo:
    name: str
    options: list[tuple[str, str]]

class FormParser(HTMLParser):
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
            if self._table is None:
                self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
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
            text = html.unescape("".join(self._option_text)).strip()
            self._options.append((self._option_value, re.sub(r"\s+", " ", text)))
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
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def parse_page(body: bytes) -> FormParser:
    parser = FormParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser


def request_page(opener, data: dict[str, str] | None = None):
    encoded = urlencode(data).encode("utf-8") if data is not None else None
    request = Request(SEARCH_URL, data=encoded, headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Referer": SEARCH_URL}, method="POST" if data is not None else "GET")
    with opener.open(request, timeout=60) as response:
        return response.geturl(), response.read(), dict(response.headers.items()), getattr(response, "status", None)


def postback(opener, parser: FormParser, target: str, license_type: str):
    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = target
    payload["__EVENTARGUMENT"] = ""
    payload[BUSINESS_UNIT] = "HHF"
    payload[LICENSE_TYPE] = license_type
    final_url, raw, headers, status = request_page(opener, payload)
    refreshed = parse_page(raw)
    return refreshed, raw, headers, {"target": target, "status": status, "final_url": final_url, "bytes": len(raw), "viewstate_refreshed": bool(refreshed.hidden.get("__VIEWSTATE"))}


def inspect_type(license_type: str) -> dict[str, object]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    _url, raw, _headers, _status = request_page(opener)
    parser = parse_page(raw)
    parser, _raw, _headers, selection = postback(opener, parser, LICENSE_TYPE, license_type)
    parser, searched, _headers, search = postback(opener, parser, SEARCH_TARGET, license_type)
    text = searched.decode("utf-8", errors="replace")
    anchors = [a for a in parser.anchors if a.get("text") or "postback" in a.get("href", "").lower()]
    interesting_anchors = [a for a in anchors if any(k in (a.get("text", "") + " " + a.get("href", "")).lower() for k in ("view", "detail", "page", "next", "license"))]
    return {
        "license_type": license_type,
        "selection": selection,
        "search": search,
        "table_count": len(parser.tables),
        "tables": [{"rows": len(table), "sample": table[:6]} for table in parser.tables[-5:]],
        "interesting_anchors": interesting_anchors[:40],
        "postback_targets": sorted(set(re.findall(r"__doPostBack\('([^']+)'\s*,\s*'([^']*)'\)", text)))[:80],
        "result_markers": [m.group(0)[:220] for m in re.finditer(r".{0,80}(?:View Detail|License No|License Number|Facility Name|Page \d+ of \d+).{0,120}", text, flags=re.I|re.S)][:30],
    }


def main() -> int:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    final_url, raw, _headers, _status = request_page(opener)
    parser = parse_page(raw)
    license_options = {value: text for select in parser.selects if select.name == LICENSE_TYPE for value, text in select.options}
    expected = {"AGC", "SNF", "SFD"}
    missing = sorted(expected - set(license_options))
    if missing:
        raise SystemExit(f"Missing expected Nevada HCQC license types: {missing}")
    result = {"requested_url": SEARCH_URL, "final_url": final_url, "license_types": {code: license_options[code] for code in ("AGC", "SNF", "SFD")}, "inspections": [inspect_type(code) for code in ("AGC", "SNF", "SFD")]}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
