from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def _norm_text(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-10:] if len(digits) >= 10 else digits


def _load_candidates(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("records") or [])


def _live_valley_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row for row in rows
        if str(row.get("license_status") or "").upper() == "ACTIVE"
        and str(row.get("is_las_vegas_valley") or "").lower() == "true"
    ]


def _match_candidate(candidate: dict, live_rows: list[dict[str, str]]) -> dict:
    requested_license = str(candidate.get("license_number") or "").strip()
    if requested_license and requested_license.upper() != "UNKNOWN":
        exact = [row for row in live_rows if str(row.get("license_number") or "").strip() == requested_license]
        if len(exact) == 1:
            return {"status": "PROMOTABLE", "match_method": "EXACT_LIVE_LICENSE", "live_row": exact[0]}
        if len(exact) > 1:
            return {"status": "AMBIGUOUS", "match_method": "DUPLICATE_LIVE_LICENSE", "matches": len(exact)}
        return {"status": "NOT_IN_LIVE_VALLEY_REGISTRY", "match_method": "EXACT_LICENSE_MISS"}

    cand_phone = _norm_phone(candidate.get("phone") or "")
    cand_address = _norm_text(candidate.get("address") or "")
    cand_city = _norm_text(candidate.get("city") or "")
    matches = []
    for row in live_rows:
        phone_match = bool(cand_phone and cand_phone == _norm_phone(row.get("phone") or ""))
        address_match = bool(
            cand_address
            and cand_address != "UNKNOWN"
            and cand_address == _norm_text(row.get("address") or "")
            and cand_city == _norm_text(row.get("city") or "")
        )
        if phone_match or address_match:
            matches.append((row, phone_match, address_match))

    unique_ids = {str(row.get("license_number") or "").strip() for row, _, _ in matches}
    if len(unique_ids) == 1 and matches:
        row, phone_match, address_match = matches[0]
        method = "EXACT_PHONE_AND_ADDRESS" if phone_match and address_match else ("EXACT_PHONE" if phone_match else "EXACT_ADDRESS_CITY")
        return {"status": "PROMOTABLE", "match_method": method, "live_row": row}
    if len(unique_ids) > 1:
        return {"status": "AMBIGUOUS", "match_method": "CONTACT_IDENTITY_COLLISION", "matches": sorted(unique_ids)}
    return {"status": "NO_STRONG_LIVE_IDENTITY_MATCH", "match_method": "CONTACT_IDENTITY_MISS"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="data/nevada/staging/pca_operational_candidates.json")
    ap.add_argument("--registry", default="data/nevada/raw/hcqc_personal_care_agencies.csv")
    ap.add_argument("--output", default="reports/NEVADA_PCA_CANDIDATE_LIVE_MATCH.json")
    args = ap.parse_args()

    candidates = _load_candidates(Path(args.candidates))
    live_rows = _live_valley_rows(Path(args.registry))
    results = []
    for candidate in candidates:
        match = _match_candidate(candidate, live_rows)
        result = {
            "agency_name": candidate.get("agency_name") or "UNKNOWN",
            "candidate_license_number": candidate.get("license_number") or "UNKNOWN",
            "primary_source_url": candidate.get("primary_source_url") or "UNKNOWN",
            "status": match["status"],
            "match_method": match["match_method"],
        }
        live_row = match.get("live_row")
        if live_row:
            result.update({
                "live_agency_id": live_row.get("agency_id") or "UNKNOWN",
                "live_agency_name": live_row.get("agency_name") or "UNKNOWN",
                "live_license_number": live_row.get("license_number") or "UNKNOWN",
                "live_address": live_row.get("address") or "UNKNOWN",
                "live_city": live_row.get("city") or "UNKNOWN",
                "live_zip": live_row.get("zip") or "UNKNOWN",
                "live_phone": live_row.get("phone") or "UNKNOWN",
            })
        if "matches" in match:
            result["matches"] = match["matches"]
        results.append(result)

    payload = {
        "schema_version": "nevada-pca-candidate-live-match-v1.0.0",
        "live_valley_registry_count": len(live_rows),
        "candidate_count": len(candidates),
        "promotable_count": sum(r["status"] == "PROMOTABLE" for r in results),
        "not_promotable_count": sum(r["status"] != "PROMOTABLE" for r in results),
        "results": results,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if len(live_rows) != 363:
        raise SystemExit(f"Expected 363 live Valley PCA licenses, got {len(live_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
