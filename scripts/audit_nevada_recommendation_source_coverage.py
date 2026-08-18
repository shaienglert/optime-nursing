from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+Nevada facility coverage audit)"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(value: object) -> str:
    value = html.unescape(str(value or "")).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def norm_addr(value: object) -> str:
    text = f" {norm(value)} "
    replacements = {
        " street ": " st ", " road ": " rd ", " avenue ": " ave ",
        " boulevard ": " blvd ", " drive ": " dr ", " lane ": " ln ",
        " court ": " ct ", " circle ": " cir ", " highway ": " hwy ",
        " parkway ": " pkwy ", " north ": " n ", " south ": " s ",
        " east ": " e ", " west ": " w ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def zip5(value: object) -> str:
    m = re.search(r"\b(\d{5})", str(value or ""))
    return m.group(1) if m else "UNKNOWN"


def strip_html(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def fetch_text(url: str) -> dict[str, object]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": "REACHABLE",
                "http_status": getattr(response, "status", None),
                "final_url": response.geturl(),
                "bytes": len(raw.encode("utf-8")),
                "text": strip_html(raw),
            }
    except Exception as exc:
        return {
            "url": url,
            "status": "UNREACHABLE_OR_BLOCKED",
            "error": type(exc).__name__,
            "message": str(exc)[:220],
            "text": "",
        }


def scope_records(records: list[dict], scope: str) -> list[dict]:
    valley = [r for r in records if r.get("is_las_vegas_valley") is True]
    if scope == "LAS_VEGAS_VALLEY":
        return valley
    if scope == "LAS_VEGAS_VALLEY_ASSISTED_LIVING_RFG":
        return [r for r in valley if r.get("canonical_type") == "ASSISTED_LIVING_RFG"]
    if scope == "LAS_VEGAS_VALLEY_SKILLED_NURSING":
        return [r for r in valley if r.get("canonical_type") == "SKILLED_NURSING"]
    if scope == "CARE_FACILITIES":
        return [r for r in records if r.get("canonical_type") in {"ASSISTED_LIVING_RFG", "SKILLED_NURSING"}]
    if scope == "NEVADA_LICENSED_CARE_FACILITIES":
        return [r for r in records if r.get("nevada_license_id") not in {None, "", "UNKNOWN"}]
    return []


def listing_match(record: dict, normalized_pages: str) -> bool:
    address = norm_addr(record.get("address"))
    z = zip5(record.get("zip"))
    name = norm(record.get("facility_name"))
    if not address or z == "UNKNOWN":
        return False
    # Strong directory identity: address plus ZIP. Name is intentionally not sufficient.
    if f"{address} {z}" in normalized_pages:
        return True
    # Some pages insert the city between address and ZIP.
    city = norm(record.get("city"))
    if city and f"{address} {city} {z}" in normalized_pages:
        return True
    # A source may omit punctuation but preserve name/address/ZIP in a different order.
    return bool(name and address in normalized_pages and z in normalized_pages and name in normalized_pages)


def claimed_listing_count(text: str) -> int | str:
    patterns = [
        r"\b(\d{1,5})\s+(?:licensed\s+)?(?:homes|results|providers|communities|facilities)\b",
        r"\b(?:results|providers|communities|facilities)\s*[:\-]?\s*(\d{1,5})\b",
    ]
    values: list[int] = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            try:
                values.append(int(m.group(1)))
            except Exception:
                pass
    return max(values) if values else "UNKNOWN"


def audit_directory(source: dict, records: list[dict]) -> dict:
    denominator = scope_records(records, source.get("denominator_scope", "NOT_APPLICABLE"))
    fetches = [fetch_text(url) for url in source.get("urls", [])]
    reachable = [f for f in fetches if f.get("status") == "REACHABLE"]
    page_text = " ".join(str(f.get("text") or "") for f in reachable)
    normalized_pages = norm_addr(page_text)
    matched = [r for r in denominator if listing_match(r, normalized_pages)] if reachable else []
    claimed = [claimed_listing_count(str(f.get("text") or "")) for f in reachable]
    claimed_numeric = [x for x in claimed if isinstance(x, int)]
    return {
        "source_name": source["name"],
        "source_role": source["role"],
        "denominator_scope": source["denominator_scope"],
        "source_status": "LIVE_FETCHED" if reachable else "SOURCE_UNAVAILABLE_OR_BLOCKED",
        "denominator_facilities": len(denominator),
        "covered_facilities_strong_identity": len(matched) if reachable else "UNKNOWN",
        "missing_vs_scope": len(denominator) - len(matched) if reachable else "UNKNOWN",
        "coverage_pct": round(100 * len(matched) / len(denominator), 2) if reachable and denominator else "UNKNOWN",
        "source_claimed_listing_count_max": max(claimed_numeric) if claimed_numeric else "UNKNOWN",
        "matched_canonical_ids": [r.get("canonical_id") for r in matched],
        "unique_additions": "UNKNOWN_NOT_ASSERTED_WITHOUT_STRONG_SOURCE_RECORD_IDENTITY",
        "precision_false_positive_concerns": source.get("precision_concern") or "Directory listing/category claims are enrichment only; exact address+ZIP is required for canonical coverage matching.",
        "fetches": [{k: v for k, v in f.items() if k != "text"} for f in fetches],
    }


def audit_structured(source: dict, records: list[dict]) -> dict:
    denominator = scope_records(records, source.get("denominator_scope", "NOT_APPLICABLE"))
    name = source["name"]
    if name == "Deficiency Reports":
        matched = []
        for r in denominator:
            detail = r.get("official_detail")
            if isinstance(detail, dict) and (detail.get("inspection_rows") or detail.get("inspection_count_on_detail_surface", 0)):
                matched.append(r)
        return {
            "source_name": name, "source_role": source["role"], "denominator_scope": source["denominator_scope"],
            "source_status": "PARTIAL_STRUCTURED_OFFICIAL_EVIDENCE",
            "denominator_facilities": len(denominator), "covered_facilities_strong_identity": len(matched),
            "missing_vs_scope": len(denominator) - len(matched),
            "coverage_pct": round(100 * len(matched) / len(denominator), 2) if denominator else "UNKNOWN",
            "unique_additions": 0,
            "precision_false_positive_concerns": "Current structured SOD extraction is strongest for AGC detail surfaces; a missing row is UNKNOWN and not proof of no deficiency.",
            "matched_canonical_ids": [r.get("canonical_id") for r in matched],
        }
    if name == "License Actions":
        matched = [r for r in denominator if str(r.get("disciplinary_action") or "").upper() not in {"", "N", "NO", "UNKNOWN"}]
        return {
            "source_name": name, "source_role": source["role"], "denominator_scope": source["denominator_scope"],
            "source_status": "STRUCTURED_OFFICIAL_FIELD",
            "denominator_facilities": len(denominator), "covered_facilities_strong_identity": len(matched),
            "missing_vs_scope": "NOT_APPLICABLE_NO_ACTION_IS_NOT_MISSING_SOURCE",
            "coverage_pct": "NOT_APPLICABLE",
            "unique_additions": 0,
            "precision_false_positive_concerns": "Counts explicit disciplinary-action evidence only; N/UNKNOWN is not interpreted as a comprehensive legal-history assertion.",
            "matched_canonical_ids": [r.get("canonical_id") for r in matched],
        }
    if name == "Fines":
        return {
            "source_name": name, "source_role": source["role"], "denominator_scope": source["denominator_scope"],
            "source_status": "NO_STRUCTURED_FINE_ADAPTER_YET",
            "denominator_facilities": len(denominator), "covered_facilities_strong_identity": "UNKNOWN",
            "missing_vs_scope": "UNKNOWN", "coverage_pct": "UNKNOWN", "unique_additions": "UNKNOWN",
            "precision_false_positive_concerns": "No fine amount/source is currently ingested; reporting zero would falsely imply no fines.",
        }
    return {}


def audit_non_directory(source: dict) -> dict:
    return {
        "source_name": source["name"],
        "source_role": source["role"],
        "denominator_scope": source.get("denominator_scope", "NOT_APPLICABLE"),
        "source_status": "ENRICHMENT_SOURCE_NOT_AN_EXHAUSTIVE_FACILITY_DIRECTORY",
        "denominator_facilities": "NOT_APPLICABLE",
        "covered_facilities_strong_identity": "NOT_APPLICABLE",
        "missing_vs_scope": "NOT_APPLICABLE",
        "coverage_pct": "NOT_APPLICABLE",
        "unique_additions": "NOT_APPLICABLE",
        "precision_false_positive_concerns": source.get("coverage_semantics") or "Not an exhaustive facility-universe discovery source.",
    }


def build(universe: dict, registry: dict) -> dict:
    records = list(universe.get("records") or [])
    governed = list(registry.get("governed_recommendation_sources") or [])
    supplemental = list(registry.get("supplemental_directory_sources") or [])
    rows = []
    for source in governed:
        if source["name"] in {"Deficiency Reports", "Fines", "License Actions"}:
            rows.append(audit_structured(source, records))
        elif source.get("urls"):
            rows.append(audit_directory(source, records))
        else:
            rows.append(audit_non_directory(source))
    supplemental_rows = [audit_directory(source, records) for source in supplemental]
    auditable = [r for r in rows + supplemental_rows if isinstance(r.get("denominator_facilities"), int)]
    return {
        "schema_version": "nevada-recommendation-source-coverage-v1.0.0",
        "generated_at": utcnow(),
        "canonical_facilities": len(records),
        "las_vegas_valley_facilities": sum(r.get("is_las_vegas_valley") is True for r in records),
        "governed_source_count": len(governed),
        "governed_sources": rows,
        "supplemental_directory_count": len(supplemental),
        "supplemental_directories": supplemental_rows,
        "auditable_scope_rows": len(auditable),
        "truth_policy": registry.get("truth_policy") or {},
        "interpretation": [
            "Coverage is measured only when the source has a meaningful facility-universe denominator.",
            "Exact normalized address+ZIP is the default directory match; name alone never proves identity.",
            "SOURCE_UNAVAILABLE_OR_BLOCKED produces UNKNOWN, never zero coverage.",
            "Unique additions remain UNKNOWN unless a source record can be strongly identified and proven absent from the canonical universe.",
            "Directories and recommendation sources never override Nevada HCQC/ALiS licensing truth.",
        ],
    }


def write_report(result: dict, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Nevada Recommendation / Directory Coverage Audit", "",
        f"Generated: `{result['generated_at']}`", "",
        f"- Canonical facilities statewide: **{result['canonical_facilities']}**",
        f"- Las Vegas Valley canonical facilities: **{result['las_vegas_valley_facilities']}**",
        f"- Governed recommendation/enrichment sources: **{result['governed_source_count']}**",
        f"- Supplemental directories audited: **{result['supplemental_directory_count']}**", "",
        "## Governed sources", "",
        "| Source | Role | Scope | Status | Covered | Denominator | Missing | Coverage |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in result["governed_sources"]:
        lines.append(f"| {row['source_name']} | {row['source_role']} | {row['denominator_scope']} | {row['source_status']} | {row['covered_facilities_strong_identity']} | {row['denominator_facilities']} | {row['missing_vs_scope']} | {row['coverage_pct']} |")
    lines += ["", "## Supplemental directories", "", "| Source | Scope | Status | Covered | Denominator | Missing | Coverage |", "|---|---|---|---:|---:|---:|---:|"]
    for row in result["supplemental_directories"]:
        lines.append(f"| {row['source_name']} | {row['denominator_scope']} | {row['source_status']} | {row['covered_facilities_strong_identity']} | {row['denominator_facilities']} | {row['missing_vs_scope']} | {row['coverage_pct']} |")
    lines += ["", "## Guardrails", ""] + [f"- {x}" for x in result["interpretation"]]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", type=Path, default=Path("database/nevada_facility_universe_canonical.json"))
    ap.add_argument("--registry", type=Path, default=Path("data/nevada/coverage/recommendation_source_registry.json"))
    ap.add_argument("--output", type=Path, default=Path("reports/NEVADA_RECOMMENDATION_SOURCE_COVERAGE.json"))
    ap.add_argument("--markdown", type=Path, default=Path("reports/NEVADA_RECOMMENDATION_SOURCE_COVERAGE.md"))
    args = ap.parse_args()
    universe = json.loads(args.universe.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = build(universe, registry)
    write_report(result, args.output, args.markdown)
    print(json.dumps({
        "canonical_facilities": result["canonical_facilities"],
        "las_vegas_valley_facilities": result["las_vegas_valley_facilities"],
        "governed_source_count": result["governed_source_count"],
        "supplemental_directory_count": result["supplemental_directory_count"],
        "sources": [{"source": r["source_name"], "status": r["source_status"], "covered": r["covered_facilities_strong_identity"], "denominator": r["denominator_facilities"]} for r in result["governed_sources"] + result["supplemental_directories"]],
    }, indent=2))
    if result["governed_source_count"] != 16:
        raise SystemExit(f"Expected exactly 16 governed recommendation/enrichment sources, got {result['governed_source_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
