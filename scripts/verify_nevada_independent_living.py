from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"


def norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def norm_addr(value: object) -> str:
    text = f" {norm(value)} "
    for a, b in {
        " street ": " st ",
        " road ": " rd ",
        " avenue ": " ave ",
        " boulevard ": " blvd ",
        " drive ": " dr ",
        " north ": " n ",
        " south ": " s ",
        " east ": " e ",
        " west ": " w ",
    }.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def probe(url: str) -> dict[str, object]:
    if not url.startswith("http"):
        return {"attempted": False, "status": "UNKNOWN"}
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urlopen(req, timeout=20) as response:
            return {
                "attempted": True,
                "http_status": getattr(response, "status", None),
                "final_url": response.geturl(),
                "status": "REACHABLE",
            }
    except Exception as exc:
        return {
            "attempted": True,
            "status": "UNREACHABLE_OR_BLOCKED",
            "error": type(exc).__name__,
            "message": str(exc)[:180],
        }


def verify(candidates: list[dict], evidence_payload: dict, *, probe_primary: bool = True) -> dict:
    evidence_rows = evidence_payload.get("records") or []
    by_license = {str(row.get("business_license_number") or "").strip(): row for row in evidence_rows}
    active_candidates: dict[str, dict] = {}
    for row in candidates:
        if row.get("license_category") != "Apartment House":
            continue
        if row.get("independent_living_classification") not in {"CANDIDATE_NAME_ONLY", "CANDIDATE_NAME_SIGNAL"}:
            continue
        if row.get("license_status") != "Active":
            continue
        lic = str(row.get("license_number") or "").strip()
        if lic and lic not in active_candidates:
            active_candidates[lic] = row

    verified: list[dict] = []
    identity_failures: list[dict] = []
    for lic, candidate in sorted(active_candidates.items()):
        evidence = by_license.get(lic)
        if evidence is None:
            verified.append({
                "business_license_number": lic,
                "business_name": candidate.get("business_name") or "UNKNOWN",
                "address": candidate.get("address") or "UNKNOWN",
                "city": candidate.get("city") or "UNKNOWN",
                "state": candidate.get("state") or "NV",
                "zip": candidate.get("zip") or "UNKNOWN",
                "classification": "UNKNOWN",
                "canonical_type": "UNKNOWN",
                "identity_verified": False,
                "evidence_summary": "No governed primary-evidence record exists for this active candidate.",
                "primary_source_url": "UNKNOWN",
                "source_role": "DISCOVERY_ENRICHMENT_ONLY",
            })
            continue

        expected_name = norm(evidence.get("expected_business_name"))
        actual_name = norm(candidate.get("business_name"))
        expected_address = norm_addr(evidence.get("expected_address"))
        actual_address = norm_addr(candidate.get("address"))
        name_ok = expected_name == actual_name
        address_ok = expected_address == actual_address or expected_address in actual_address or actual_address in expected_address
        identity_ok = bool(name_ok and address_ok)
        if not identity_ok:
            identity_failures.append({
                "business_license_number": lic,
                "expected_name": evidence.get("expected_business_name"),
                "actual_name": candidate.get("business_name"),
                "expected_address": evidence.get("expected_address"),
                "actual_address": candidate.get("address"),
            })

        governed_classification = str(evidence.get("classification") or "UNKNOWN") if identity_ok else "UNKNOWN"
        primary_url = str(evidence.get("primary_source_url") or "UNKNOWN")
        live_probe = probe(primary_url) if probe_primary and primary_url.startswith("http") else {"attempted": False, "status": "NOT_REQUESTED"}
        verified.append({
            "business_license_number": lic,
            "business_name": candidate.get("business_name") or "UNKNOWN",
            "legal_name": candidate.get("legal_name") or "UNKNOWN",
            "address": candidate.get("address") or "UNKNOWN",
            "city": candidate.get("city") or "UNKNOWN",
            "state": candidate.get("state") or "NV",
            "zip": candidate.get("zip") or "UNKNOWN",
            "business_license_status": candidate.get("license_status") or "UNKNOWN",
            "classification": governed_classification,
            "canonical_type": "INDEPENDENT_LIVING" if governed_classification == "CONFIRMED_PRIMARY" else "UNKNOWN",
            "identity_verified": identity_ok,
            "primary_source_url": primary_url,
            "secondary_primary_source_url": evidence.get("secondary_primary_source_url") or "UNKNOWN",
            "evidence_summary": evidence.get("evidence_summary") or "UNKNOWN",
            "care_services_inferred": False,
            "source_role": "PRIMARY_OPERATOR_OR_PROVIDER_EVIDENCE" if governed_classification in {"CONFIRMED_PRIMARY", "NOT_INDEPENDENT_LIVING_PRIMARY"} else "DISCOVERY_ENRICHMENT_ONLY",
            "primary_source_live_probe": live_probe,
        })

    counts = {
        "active_unique_candidates": len(active_candidates),
        "confirmed_primary": sum(row["classification"] == "CONFIRMED_PRIMARY" for row in verified),
        "not_independent_living_primary": sum(row["classification"] == "NOT_INDEPENDENT_LIVING_PRIMARY" for row in verified),
        "unknown": sum(row["classification"] == "UNKNOWN" for row in verified),
        "identity_failures": len(identity_failures),
        "primary_urls_reachable": sum((row.get("primary_source_live_probe") or {}).get("status") == "REACHABLE" for row in verified),
    }
    return {
        "schema_version": "nevada-independent-living-verification-v1.0.0",
        "generated_at": utcnow(),
        "policy": evidence_payload.get("policy") or {},
        "counts": counts,
        "identity_failures": identity_failures,
        "records": verified,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=Path, default=Path("data/nevada/raw/las_vegas_business_license_senior_candidates.json"))
    ap.add_argument("--evidence", type=Path, default=Path("data/nevada/verified/independent_living_primary_evidence.json"))
    ap.add_argument("--output", type=Path, default=Path("data/nevada/verified/independent_living_verification.json"))
    ap.add_argument("--report", type=Path, default=Path("reports/NEVADA_INDEPENDENT_LIVING_VERIFICATION.json"))
    ap.add_argument("--no-live-probe", action="store_true")
    args = ap.parse_args()

    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    result = verify(candidates, evidence, probe_primary=not args.no_live_probe)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({
        "generated_at": result["generated_at"],
        "counts": result["counts"],
        "identity_failures": result["identity_failures"],
        "policy": result["policy"],
        "output": str(args.output),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], indent=2))

    if result["counts"]["identity_failures"]:
        raise SystemExit("Independent Living evidence identity mismatch; classifications were held UNKNOWN")
    if result["counts"]["active_unique_candidates"] == 0:
        raise SystemExit("No active Independent Living candidates found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
