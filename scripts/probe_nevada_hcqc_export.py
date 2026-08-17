from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"

@dataclass
class SelectInfo:
    name: str
    options: list[tuple[str, str]]

class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden: dict[str, str] = {}
        self.selects: list[SelectInfo] = []
        self.inputs: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self._select_name: str | None = None
        self._options: list[tuple[str, str]] = []
        self._option_value = ""
        self._option_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self.forms.append(a)
        elif tag == "input":
            self.inputs.append(a)
            if a.get("type", "").lower() == "hidden" and a.get("name"):
                self.hidden[a["name"]] = a.get("value", "")
        elif tag == "select":
            self._select_name = a.get("name") or a.get("id")
            self._options = []
        elif tag == "option" and self._select_name:
            self._option_value = a.get("value", "")
            self._option_text = []

    def handle_data(self, data: str) -> None:
        if self._select_name:
            self._option_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._select_name:
            text = html.unescape("".join(self._option_text)).strip()
            self._options.append((self._option_value, re.sub(r"\s+", " ", text)))
            self._option_text = []
        elif tag == "select" and self._select_name:
            self.selects.append(SelectInfo(self._select_name, self._options))
            self._select_name = None
            self._options = []


def fetch() -> tuple[str, str]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    req = Request(SEARCH_URL, headers={"User-Agent": UA})
    with opener.open(req, timeout=45) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


def keep_attrs(item: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in item.items() if k in {"name", "id", "value", "type", "title", "alt", "src", "onclick"}}


def main() -> int:
    final_url, body = fetch()
    parser = FormParser()
    parser.feed(body)
    wanted = []
    for select in parser.selects:
        matching = [
            {"value": value, "text": text}
            for value, text in select.options
            if any(token in text.lower() for token in (
                "health facilit", "residential facility", "skilled nursing", "nursing facilit", "continuing care"
            ))
        ]
        if matching:
            wanted.append({"name": select.name, "matching_options": matching, "option_count": len(select.options)})
    export_controls = [
        keep_attrs(control)
        for control in parser.inputs
        if any(token in " ".join(control.values()).lower() for token in ("excel", "export", "generate"))
    ]
    actionable_controls = [
        keep_attrs(control)
        for control in parser.inputs
        if control.get("type", "").lower() in {"submit", "button", "image"}
    ]
    result = {
        "requested_url": SEARCH_URL,
        "final_url": final_url,
        "html_bytes": len(body.encode("utf-8")),
        "form": parser.forms[0] if parser.forms else None,
        "hidden_field_names": sorted(parser.hidden),
        "relevant_selects": wanted,
        "export_controls": export_controls,
        "actionable_controls": actionable_controls[:40],
        "contains_generate_excel": "generate excel" in body.lower(),
    }
    print(json.dumps(result, indent=2))
    if not wanted:
        raise SystemExit("HCQC page loaded, but no relevant facility-type option was discoverable")
    if not result["contains_generate_excel"]:
        raise SystemExit("HCQC page did not expose Generate Excel")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
