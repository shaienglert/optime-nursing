from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "backend" / "optime_nursing.db"
CONTROLLED = ROOT / "reports" / "CONTROLLED_POST_STROKE_APPLES_TO_APPLES_AUDIT.json"
OUT_JSON = ROOT / "reports" / "TARGETED_GAP_RESEARCH.json"
OUT_MD = ROOT / "reports" / "TARGETED_GAP_RESEARCH.md"

KEY_NAMES = [
    "JOHN KNOX VILLAGE OF POMPANO BEACH",
    "RIVER GARDEN HEBREW HOME FOR THE AGED",
    "SANDS AT SOUTH BEACH CARE CENTER, THE",
    "BISCAYNE HEALTH AND REHABILITATION CENTER",
    "CORAL GABLES NURSING AND REHABILITATION CENTER",
    "PINECREST CENTER FOR REHABILITATION AND HEALING",
    "FOUNTAIN MANOR HEALTH & REHABILITATION CENTER",
]


def read_controlled_top_candidates() -> list[str]:
    if not CONTROLLED.exists():
        return KEY_NAMES
    payload = json.loads(CONTROLLED.read_text(encoding="utf-8"))
    top = [str(r.get("facility") or "").strip().upper() for r in payload.get("decision_table_sorted_by_rank", [])[:10]]
    top = [name for name in top if name]
    merged = []
    seen = set()
    for name in KEY_NAMES + top:
        upper = name.strip().upper()
        if upper and upper not in seen:
            seen.add(upper)
            merged.append(upper)
    return merged


def map_names_to_ids(conn: sqlite3.Connection, names: list[str]) -> list[dict]:
    cur = conn.cursor()
    rows = []
    for name in names:
        row = cur.execute(
            """
            select id, cms_id, name, city, state
            from facilities
            where upper(name)=?
            limit 1
            """,
            (name,),
        ).fetchone()
        if row:
            rows.append(
                {
                    "facility_id": int(row[0]),
                    "cms_id": str(row[1]) if row[1] is not None else None,
                    "facility_name": str(row[2]),
                    "city": str(row[3]) if row[3] is not None else None,
                    "state": str(row[4]) if row[4] is not None else None,
                }
            )
    return rows


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    names = read_controlled_top_candidates()
    facilities = map_names_to_ids(conn, names)
    facility_ids = [r["facility_id"] for r in facilities]

    import sys

    sys.path.insert(0, str((ROOT / "backend").resolve()))
    from app.database import SessionLocal
    from app.services.external_discovery import run_external_discovery

    db = SessionLocal()
    try:
        result = run_external_discovery(db, agent_key="provider_intelligence", facility_ids=facility_ids)
    finally:
        db.close()

    run_id = str(result.get("run_id") or "")
    cur = conn.cursor()

    claim_rows = cur.execute(
        """
        select facility_id, facility_name, claim_type, change_status, verification_status, source_name
        from external_source_request_logs
        where run_id=? and claim_type!='__source_attempt__'
        order by facility_name asc, id asc
        """,
        (run_id,),
    ).fetchall()

    source_attempt_rows = cur.execute(
        """
        select facility_id, facility_name, source_name, request_status, response_code, failure_reason
        from external_source_request_logs
        where run_id=? and claim_type='__source_attempt__'
        order by facility_name asc, id asc
        """,
        (run_id,),
    ).fetchall()

    by_facility_claims = {}
    for r in claim_rows:
        name = str(r["facility_name"])
        by_facility_claims.setdefault(name, []).append(
            {
                "claim_type": str(r["claim_type"]),
                "change_status": str(r["change_status"]),
                "verification_status": str(r["verification_status"]),
                "source_name": str(r["source_name"]),
            }
        )

    by_facility_attempts = {}
    for r in source_attempt_rows:
        name = str(r["facility_name"])
        by_facility_attempts.setdefault(name, []).append(
            {
                "source_name": str(r["source_name"]),
                "request_status": str(r["request_status"]),
                "response_code": r["response_code"],
                "failure_reason": str(r["failure_reason"]) if r["failure_reason"] else None,
            }
        )

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "target_facility_count": len(facility_ids),
        "target_facilities": facilities,
        "external_source_requests": int(result.get("external_source_requests", 0) or 0),
        "source_successes": int(result.get("source_successes", 0) or 0),
        "source_failures": int(result.get("source_failures", 0) or 0),
        "new_external_verified_facts": int(result.get("new_external_verified_facts", 0) or 0),
        "external_changed_facts": int(result.get("external_changed_facts", 0) or 0),
        "unknown_resolved": int(result.get("unknown_resolved", 0) or 0),
        "new_regulatory_findings": int(result.get("new_regulatory_findings", 0) or 0),
        "new_verified_services": int(result.get("new_verified_services", 0) or 0),
        "new_activity_findings": int(result.get("new_activity_findings", 0) or 0),
        "new_nutrition_findings": int(result.get("new_nutrition_findings", 0) or 0),
        "new_verified_prices": int(result.get("new_verified_prices", 0) or 0),
        "source_requests_by_status": result.get("source_requests_by_status", {}),
        "claims_by_facility": by_facility_claims,
        "source_attempts_by_facility": by_facility_attempts,
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Targeted Gap Research",
        "",
        f"- Generated: {summary['generated_at_utc']}",
        f"- Run ID: {run_id}",
        f"- Target facilities: {len(facility_ids)}",
        f"- External source requests: {summary['external_source_requests']}",
        f"- Source successes: {summary['source_successes']}",
        f"- Source failures: {summary['source_failures']}",
        f"- New verified facts: {summary['new_external_verified_facts']}",
        f"- Changed facts: {summary['external_changed_facts']}",
        f"- Unknown resolved: {summary['unknown_resolved']}",
        "",
        "## High-Value Field Discovery",
        "",
        f"- Regulatory findings: {summary['new_regulatory_findings']}",
        f"- Verified clinical services: {summary['new_verified_services']}",
        f"- Activities findings: {summary['new_activity_findings']}",
        f"- Nutrition findings: {summary['new_nutrition_findings']}",
        f"- Pricing findings: {summary['new_verified_prices']}",
        "",
        "## Source Request Status",
        "",
    ]
    for k, v in sorted((summary.get("source_requests_by_status") or {}).items()):
        lines.append(f"- {k}: {v}")

    lines.extend(["", "## Per Facility Summary", ""])
    for fac in facilities:
        name = fac["facility_name"]
        claims = by_facility_claims.get(name, [])
        attempts = by_facility_attempts.get(name, [])
        lines.append(f"### {name}")
        lines.append(f"- Claims captured: {len(claims)}")
        lines.append(f"- Source attempts: {len(attempts)}")
        if attempts:
            statuses = {}
            for a in attempts:
                statuses[a["request_status"]] = statuses.get(a["request_status"], 0) + 1
            for s, c in sorted(statuses.items()):
                lines.append(f"- {s}: {c}")
        lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"run_id": run_id, "output_json": str(OUT_JSON), "output_md": str(OUT_MD)}, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
