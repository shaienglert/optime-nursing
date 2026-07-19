from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.email_service import configured_recipients, send_email  # noqa: E402
from app.services.evidence_source_integrity import audit_traceability  # noqa: E402


REPORT_PATH = REPO_ROOT / "reports" / "audits" / "EVIDENCE_SOURCE_INTEGRITY_REPORT.md"


def _write_report(content: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content.rstrip() + "\n", encoding="utf-8")


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    def esc(v: object) -> str:
        return str(v).replace("|", "\\|")

    out = []
    out.append(f"| {' | '.join(esc(h) for h in headers)} |")
    out.append(f"| {' | '.join('---' for _ in headers)} |")
    for row in rows:
        out.append(f"| {' | '.join(esc(x) for x in row)} |")
    return "\n".join(out)


def _build_report(payload: Dict[str, object], email_status: Dict[str, object]) -> str:
    metrics = payload["metrics"]
    tier_dist = payload["source_tier_distribution"]
    gaps = payload["critical_evidence_gaps"]
    conflicts = payload["value_conflicts_detected"]

    lines: List[str] = []
    lines.append("# EVIDENCE_SOURCE_INTEGRITY_REPORT")
    lines.append("")
    lines.append(f"- Generated At (UTC): **{datetime.now(timezone.utc).isoformat()}**")
    lines.append("- Scope: recommendation-eligible material claims in active knowledge objects")
    lines.append("")
    lines.append("## Source Hierarchy Implemented")
    lines.append("")
    lines.append(_md_table(
        ["Tier", "Authority Type", "Examples", "Base Confidence"],
        [
            ["TIER_1", "Authoritative / Regulatory", "AHCA, CMS, Medicare Care Compare, state inspections", "0.92"],
            ["TIER_2", "Independent Professional / Scientific", "Peer-reviewed journals, clinical guidelines, professional orgs", "0.82"],
            ["TIER_3", "Independent Experience / Observational", "Google Reviews, Yelp, Caring.com, SeniorAdvisor", "0.62"],
            ["TIER_4", "Provider-reported", "Official provider websites, brochures, provider statements", "0.72"],
        ],
    ))
    lines.append("")
    lines.append("## Traceability Audit Results")
    lines.append("")
    lines.append(_md_table(
        ["Metric", "Value"],
        [
            ["Material claims audited", metrics["material_claims_audited"]],
            ["Fully traceable", metrics["fully_traceable"]],
            ["Partially traceable", metrics["partially_traceable"]],
            ["Untraceable", metrics["untraceable"]],
            ["Conflicting", metrics["conflicting"]],
            ["Stale", metrics["stale"]],
        ],
    ))
    lines.append("")
    lines.append("## Source Tier Distribution")
    lines.append("")
    lines.append(_md_table(
        ["Tier", "Count"],
        [[tier, count] for tier, count in tier_dist.items()],
    ))
    lines.append("")
    lines.append("## Conflicts Detected")
    lines.append("")
    if conflicts:
        lines.append(_md_table(
            ["Entity Key", "Property", "Distinct Values"],
            [[c["entity_key"], c["property_name"], c["distinct_values"]] for c in conflicts[:20]],
        ))
    else:
        lines.append("- None detected in current run.")
    lines.append("")
    lines.append("## Critical Evidence Gaps")
    lines.append("")
    if gaps:
        lines.extend([f"- {g}" for g in gaps[:30]])
    else:
        lines.append("- None detected in current run.")
    lines.append("")
    lines.append("## Fixes Completed")
    lines.append("")
    lines.append("- Added canonical source-tier classification and claim-type-aware confidence logic.")
    lines.append("- Added freshness classification by claim type (CURRENT / AGING / STALE / UNKNOWN).")
    lines.append("- Added explicit traceability classification for material claims.")
    lines.append("- Added facility claim evidence trace API and recommendation score trace API.")
    lines.append("")
    lines.append("## Validation Result")
    lines.append("")
    lines.append(f"- Traceability audit executed: **PASS**")
    lines.append(f"- Material claims audited: **{metrics['material_claims_audited']}**")
    lines.append(f"- Email delivery status: **{email_status['status']}**")
    lines.append("")
    lines.append("## Email Delivery")
    lines.append("")
    lines.append(f"- Recipient(s): **{', '.join(email_status['recipients']) if email_status['recipients'] else 'UNPROVEN'}**")
    lines.append(f"- Provider response: **{email_status['provider_response']}**")

    return "\n".join(lines)


def main() -> int:
    db = SessionLocal()
    try:
        payload = audit_traceability(db)
    finally:
        db.close()

    # Build report first so generation always succeeds even if outbound delivery is blocked.
    provisional_email = {
        "status": "DELIVERY_PENDING",
        "provider_response": "pending",
        "recipients": configured_recipients(),
    }
    report_md = _build_report(payload, provisional_email)
    _write_report(report_md)

    subject = "OPTIME Evidence & Source Integrity Report"
    ok, message, recipients = send_email(
        subject=subject,
        body_text=report_md,
        recipients=configured_recipients(),
    )
    email_status = {
        "status": "DELIVERED_ACCEPTED" if ok else ("DELIVERY_BLOCKED" if "not configured" in message.lower() else "DELIVERY_FAILED"),
        "provider_response": message,
        "recipients": recipients,
    }

    final_md = _build_report(payload, email_status)
    _write_report(final_md)

    out = {
        "report_path": str(REPORT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "email_status": email_status,
        "metrics": payload["metrics"],
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
