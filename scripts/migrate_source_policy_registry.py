from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.source_lifecycle_service import (
    REGISTRY_PATH,
    STATUS_REPORT_PATH,
    ensure_registry_shape,
    evaluate_source_policy_for_record,
    generate_status_snapshot,
    list_launch_blockers,
    load_registry,
    render_status_report,
    save_registry,
    transition_source_status,
)

MIGRATION_JSON_PATH = REPO_ROOT / "reports" / "SOURCE_POLICY_MIGRATION_REPORT.json"
MIGRATION_MD_PATH = REPO_ROOT / "reports" / "SOURCE_POLICY_MIGRATION_REPORT.md"


def migrate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    shaped = ensure_registry_shape(payload)
    changes: List[Dict[str, Any]] = []
    before_status: Dict[str, int] = {}

    for record in shaped["records"]:
        previous_status = str(record.get("lifecycle_status") or "")
        before_status[previous_status] = before_status.get(previous_status, 0) + 1
        previous_policy = str(record.get("policy_status") or "UNSET")
        outcome = evaluate_source_policy_for_record(record)
        proposed = outcome["proposed_lifecycle_status"]
        if proposed != previous_status:
            transition_source_status(
                record,
                proposed,
                reason_codes=outcome["policy_reason_codes"],
                next_review_date=record.get("next_review_date"),
                last_successful_import=record.get("last_successful_import"),
                allow_owner_override=True,
            )
        else:
            record["updated_at"] = record.get("updated_at") or outcome["policy_version"]
        changes.append(
            {
                "source_id": record["source_id"],
                "source_name": record["source_name"],
                "market": record["market"],
                "status_before": previous_status,
                "status_after": record["lifecycle_status"],
                "policy_before": previous_policy,
                "policy_after": record["policy_status"],
                "policy_confidence": record["policy_confidence"],
                "reason_codes": list(record.get("policy_reason_codes") or []),
                "owner_review_required": bool(record.get("policy_owner_review_required")),
                "unresolved_evidence_gaps": list(record.get("policy_missing_evidence") or []),
            }
        )

    return {
        "payload": shaped,
        "changes": changes,
        "before_status_distribution": before_status,
    }


def build_migration_report(payload: Dict[str, Any], before_status_distribution: Dict[str, int], changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    snapshot = generate_status_snapshot(payload)
    return {
        "generated_at_utc": snapshot["generated_at_utc"],
        "registry_record_count": snapshot["record_count"],
        "status_distribution_before": before_status_distribution,
        "status_distribution_after": snapshot["status_distribution"],
        "owner_decision_count": snapshot["owner_decision_count"],
        "owner_decision_percentage": snapshot["owner_decision_percentage"],
        "launch_blockers": [
            {
                "source_id": record["source_id"],
                "market": record["market"],
                "lifecycle_status": record["lifecycle_status"],
                "policy_status": record.get("policy_status"),
                "failure_category": record.get("failure_category"),
            }
            for record in list_launch_blockers(payload)
        ],
        "sources_due_for_retry": [record["source_id"] for record in snapshot["sources_due_for_retry"]],
        "sources_due_for_validation": [record["source_id"] for record in snapshot["sources_due_for_validation"]],
        "policy_version_distribution": snapshot["policy_version_distribution"],
        "changes": changes,
    }


def render_migration_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Source Policy Migration Report")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at_utc']}`")
    lines.append("")
    lines.append(f"- Registry records migrated: **{report['registry_record_count']}**")
    lines.append(f"- Owner decision required: **{report['owner_decision_count']}** ({report['owner_decision_percentage']}%)")
    lines.append("")
    lines.append("## Status Distribution Before")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("| --- | ---: |")
    for status, count in sorted(report["status_distribution_before"].items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")
    lines.append("## Status Distribution After")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("| --- | ---: |")
    for status, count in sorted(report["status_distribution_after"].items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")
    lines.append("## Policy Version Distribution")
    lines.append("")
    lines.append("| Policy Version | Count |")
    lines.append("| --- | ---: |")
    for version, count in sorted(report["policy_version_distribution"].items()):
        lines.append(f"| {version} | {count} |")
    lines.append("")
    lines.append("## Launch Blockers")
    lines.append("")
    if report["launch_blockers"]:
        lines.append("| Source ID | Market | Lifecycle | Policy | Failure Category |")
        lines.append("| --- | --- | --- | --- | --- |")
        for blocker in report["launch_blockers"]:
            lines.append(f"| {blocker['source_id']} | {blocker['market']} | {blocker['lifecycle_status']} | {blocker['policy_status']} | {blocker.get('failure_category') or ''} |")
    else:
        lines.append("No launch blockers.")
    lines.append("")
    lines.append("## Source Changes")
    lines.append("")
    lines.append("| Source ID | Market | Status Before | Status After | Policy Decision | Confidence | Owner Review | Reason Codes | Gaps |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for change in report["changes"]:
        lines.append(
            f"| {change['source_id']} | {change['market']} | {change['status_before']} | {change['status_after']} | {change['policy_after']} | {change['policy_confidence']} | {'YES' if change['owner_review_required'] else 'NO'} | {', '.join(change['reason_codes'])} | {', '.join(change['unresolved_evidence_gaps'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = load_registry(REGISTRY_PATH)
    migration = migrate_payload(payload)
    saved = save_registry(migration["payload"], REGISTRY_PATH)

    status_report = render_status_report(saved)
    STATUS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_REPORT_PATH.write_text(status_report, encoding="utf-8")

    migration_report = build_migration_report(saved, migration["before_status_distribution"], migration["changes"])
    MIGRATION_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_JSON_PATH.write_text(json.dumps(migration_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MIGRATION_MD_PATH.write_text(render_migration_markdown(migration_report), encoding="utf-8")

    print(json.dumps({
        "registry": str(REGISTRY_PATH),
        "status_report": str(STATUS_REPORT_PATH),
        "migration_report_json": str(MIGRATION_JSON_PATH),
        "migration_report_md": str(MIGRATION_MD_PATH),
        "record_count": saved["record_count"],
        "owner_decision_percentage": migration_report["owner_decision_percentage"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())