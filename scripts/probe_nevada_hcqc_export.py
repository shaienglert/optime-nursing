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


def get_page(opener):
    request = Request(SEARCH_URL, headers={"User-Agent": UA})
    with opener.open(request, timeout=45) as response:
        return response.geturl(), response.read(), dict(response.headers.items())


def export_type(opener, parser: FormParser, license_type: str) -> dict[str, object]:
    payload = dict(parser.hidden)
    payload["__EVENTTARGET"] = EXPORT_TARGET
    payload["__EVENTARGUMENT"] = ""
    payload[BUSINESS_UNIT] = "HHF"
    payload[LICENSE_TYPE] = license_type
    body = urlencode(payload).encode("utf-8")
    request = Request(
        SEARCH_URL,
        data=body,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": SEARCH_URL,
        },
        method="POST",
    )
    with opener.open(request, timeout=60) as response:
        raw = response.read()
        headers = dict(response.headers.items())
        content_type = headers.get("Content-Type", "")
        disposition = headers.get("Content-Disposition", "")
        signature = raw[:16].hex()
        text_prefix = raw[:240].decode("utf-8", errors="replace") if "text" in content_type.lower() or "html" in content_type.lower() else None
        return {
            "license_type": license_type,
            "status": getattr(response, "status", None),
            "final_url": response.geturl(),
            "content_type": content_type,
            "content_disposition": disposition,
            "bytes": len(raw),
            "signature_hex": signature,
            "text_prefix": text_prefix,
            "looks_like_excel": (
                raw.startswith(b"PK\x03\x04")
                or raw.startswith(bytes.fromhex("d0cf11e0a1b11ae1"))
                or "excel" in content_type.lower()
                or ".xls" in disposition.lower()
            ),
        }


def main() -> int:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    final_url, raw, _headers = get_page(opener)
    parser = parse_page(raw)
    license_options = {
        value: text
        for select in parser.selects
        if select.name == LICENSE_TYPE
        for value, text in select.options
    }
    expected = {"AGC", "SNF", "SFD"}
    missing = sorted(expected - set(license_options))
    if missing:
        raise SystemExit(f"Missing expected Nevada HCQC license types: {missing}")

    export_control = next(
        (a for a in parser.anchors if "generate excel" in a.get("text", "").lower()),
        None,
    )
    if not export_control or EXPORT_TARGET not in export_control.get("href", ""):
        raise SystemExit("Generate Excel postback target was not confirmed")

    exports = [export_type(opener, parser, code) for code in ("AGC", "SNF", "SFD")]
    result = {
        "requested_url": SEARCH_URL,
        "final_url": final_url,
        "license_types": {code: license_options[code] for code in ("AGC", "SNF", "SFD")},
        "export_target": EXPORT_TARGET,
        "exports": exports,
    }
    print(json.dumps(result, indent=2))
    failed = [item for item in exports if not item["looks_like_excel"]]
    if failed:
        raise SystemExit(f"Nevada HCQC export did not return Excel for: {[item['license_type'] for item in failed]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
