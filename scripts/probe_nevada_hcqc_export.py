from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor

SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"
BUSINESS_UNIT = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$ddlBusinessUnit"
LICENSE_TYPE = "ctl00$ContentPlaceHolder1$ucLicenseeSearchPublic$cmbLicenseType"
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
        self._select_name: str | None = None
        self._options: list[tuple[str, str]] = []
        self._option_value = ""
        self._option_text: list[str] = []
        self._anchor_attrs: dict[str, str] | None = None
        self._anchor_text: list[str] = []

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

    def handle_data(self, data: str) -> None:
        if self._select_name:
            self._option_text.append(data)
        if self._anchor_attrs is not None:
            self._anchor_text.append(data)

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


def parse_page(body: bytes) -> FormParser:
    parser = FormParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser


def request_page(opener, data: dict[str, str] | None = None):
    encoded = urlencode(data).encode("utf-8") if data is not None else None
    request = Request(
        SEARCH_URL,
        data=encoded,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Referer": SEARCH_URL},
        method="POST" if data is not None else "GET",
    )
    with opener.open(request, timeout=60) as response:
        return response.geturl(), response.read(), dict(response.headers.items()), getattr(response, "status", None)


def state_postback(opener, parser: FormParser, target: str, license_type: str) -> tuple[FormParser, dict[str, object]]:
    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = target
    payload["__EVENTARGUMENT"] = ""
    payload[BUSINESS_UNIT] = "HHF"
    payload[LICENSE_TYPE] = license_type
    final_url, raw, headers, status = request_page(opener, payload)
    refreshed = parse_page(raw)
    return refreshed, {"target": target, "license_type": license_type, "status": status, "final_url": final_url, "content_type": headers.get("Content-Type", ""), "bytes": len(raw), "viewstate_refreshed": bool(refreshed.hidden.get("__VIEWSTATE"))}


def export_type(license_type: str) -> dict[str, object]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    _url, raw, _headers, _status = request_page(opener)
    parser = parse_page(raw)
    parser, selection = state_postback(opener, parser, LICENSE_TYPE, license_type)
    search_controls = [a for a in parser.anchors if "search" in " ".join(a.values()).lower()]

    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = EXPORT_TARGET
    payload["__EVENTARGUMENT"] = ""
    payload[BUSINESS_UNIT] = "HHF"
    payload[LICENSE_TYPE] = license_type
    final_url, exported, headers, status = request_page(opener, payload)
    content_type = headers.get("Content-Type", "")
    disposition = headers.get("Content-Disposition", "")
    return {
        "license_type": license_type,
        "selection_postback": selection,
        "search_controls_after_selection": search_controls[:12],
        "status": status,
        "final_url": final_url,
        "content_type": content_type,
        "content_disposition": disposition,
        "bytes": len(exported),
        "signature_hex": exported[:16].hex(),
        "text_prefix": exported[:320].decode("utf-8", errors="replace") if "html" in content_type.lower() or "text" in content_type.lower() else None,
        "looks_like_excel": exported.startswith(b"PK\x03\x04") or exported.startswith(bytes.fromhex("d0cf11e0a1b11ae1")) or "excel" in content_type.lower() or ".xls" in disposition.lower(),
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
    export_control = next((a for a in parser.anchors if "generate excel" in a.get("text", "").lower()), None)
    if not export_control or EXPORT_TARGET not in export_control.get("href", ""):
        raise SystemExit("Generate Excel postback target was not confirmed")

    exports = [export_type(code) for code in ("AGC", "SNF", "SFD")]
    result = {"requested_url": SEARCH_URL, "final_url": final_url, "license_types": {code: license_options[code] for code in ("AGC", "SNF", "SFD")}, "export_target": EXPORT_TARGET, "exports": exports}
    print(json.dumps(result, indent=2))
    failed = [item for item in exports if not item["looks_like_excel"]]
    if failed:
        raise SystemExit(f"Nevada HCQC export did not return Excel after selection postback for: {[item['license_type'] for item in failed]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
