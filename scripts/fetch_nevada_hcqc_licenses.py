from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "nevada" / "hcqc"
SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HFF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"

TARGET_PATTERNS = (
    "residential facility for groups",
    "assisted living",
    "skilled nursing",
    "nursing facility",
    "intermediate care",
    "continuing care",
    "home for individual residential care",
)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def select_with_option(page, needle: str):
    needle = normalize(needle)
    for select in page.locator("select").all():
        options = select.locator("option").all_text_contents()
        for idx, label in enumerate(options):
            if needle in normalize(label):
                option = select.locator("option").nth(idx)
                value = option.get_attribute("value")
                if value is not None:
                    select.select_option(value=value)
                else:
                    select.select_option(index=idx)
                page.wait_for_timeout(1200)
                return select, label
    return None, None


def find_credential_select(page):
    best = None
    best_labels: list[str] = []
    for select in page.locator("select").all():
        labels = [str(x).strip() for x in select.locator("option").all_text_contents()]
        joined = " | ".join(normalize(x) for x in labels)
        hits = sum(1 for pattern in TARGET_PATTERNS if pattern in joined)
        if hits > 0 and len(labels) > len(best_labels):
            best = select
            best_labels = labels
    return best, best_labels


def find_generate_excel(page):
    candidates = [
        page.get_by_text("Generate Excel", exact=False),
        page.locator("input[value*='Excel' i]"),
        page.locator("button:has-text('Excel')"),
        page.locator("a:has-text('Excel')"),
    ]
    for candidate in candidates:
        try:
            if candidate.count() and candidate.first.is_visible():
                return candidate.first
        except Exception:
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "source_url": SEARCH_URL,
        "business_unit_selected": None,
        "credential_options": [],
        "target_options": [],
        "downloads": [],
        "errors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(1500)

        _, business_label = select_with_option(page, "Health Facilities")
        manifest["business_unit_selected"] = business_label
        page.wait_for_timeout(1500)

        credential_select, labels = find_credential_select(page)
        manifest["credential_options"] = labels
        if credential_select is None:
            manifest["errors"].append("Credential Type select not found after selecting Health Facilities")
        else:
            targets = [label for label in labels if any(pattern in normalize(label) for pattern in TARGET_PATTERNS)]
            manifest["target_options"] = targets
            excel = find_generate_excel(page)
            if excel is None:
                manifest["errors"].append("Generate Excel control not found")
            else:
                for index, label in enumerate(targets, start=1):
                    try:
                        credential_select, current_labels = find_credential_select(page)
                        if credential_select is None:
                            raise RuntimeError("Credential Type select disappeared")
                        option_index = current_labels.index(label)
                        option = credential_select.locator("option").nth(option_index)
                        value = option.get_attribute("value")
                        if value is not None:
                            credential_select.select_option(value=value)
                        else:
                            credential_select.select_option(index=option_index)
                        page.wait_for_timeout(700)
                        excel = find_generate_excel(page)
                        if excel is None:
                            raise RuntimeError("Generate Excel control disappeared")
                        with page.expect_download(timeout=60_000) as info:
                            excel.click()
                        download = info.value
                        suggested = download.suggested_filename or f"nevada_hcqc_{index}.xlsx"
                        safe_label = re.sub(r"[^a-z0-9]+", "_", normalize(label)).strip("_")[:80]
                        suffix = Path(suggested).suffix or ".xlsx"
                        destination = out_dir / f"{index:02d}_{safe_label}{suffix}"
                        download.save_as(destination)
                        manifest["downloads"].append({
                            "credential_type": label,
                            "file": destination.name,
                            "size_bytes": destination.stat().st_size,
                        })
                    except Exception as exc:
                        manifest["errors"].append(f"{label}: {type(exc).__name__}: {exc}")
        browser.close()

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if manifest["business_unit_selected"] is None or not manifest["downloads"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
