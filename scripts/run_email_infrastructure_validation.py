import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.email_service import (
    provider_name,
    send_email_detailed,
    test_smtp_connection,
    validate_email_configuration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "email"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _md_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    cfg = validate_email_configuration()
    conn = test_smtp_connection()

    provider = provider_name()
    recipients = cfg.get("recipients") or []

    subject = "OPTIME Email Infrastructure Test"
    body_text = "\n".join(
        [
            "OPTIME Email Infrastructure Test",
            f"Timestamp (UTC): {now}",
            "Environment: production-workspace",
            f"Provider: {provider}",
            "Status: attempting real delivery",
        ]
    )
    body_html = (
        "<h1>OPTIME Email Infrastructure Test</h1>"
        f"<p><strong>Timestamp (UTC):</strong> {now}</p>"
        "<p><strong>Environment:</strong> production-workspace</p>"
        f"<p><strong>Provider:</strong> {provider}</p>"
        "<p><strong>Status:</strong> attempting real delivery</p>"
    )

    send_result = send_email_detailed(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        recipients=list(recipients),
        attachments=None,
    )

    cfg_report = [
        "# Email Configuration Report",
        "",
        f"- Generated At (UTC): **{now}**",
        f"- Provider: **{provider}**",
        f"- Configuration Status: **{'CONFIGURED' if cfg.get('configured') else 'MISSING_CONFIGURATION'}**",
        f"- Sender: **{cfg.get('sender') or 'UNSET'}**",
        f"- Recipient(s): **{', '.join(recipients) if recipients else 'UNSET'}**",
        f"- SMTP Host: **{cfg.get('host') or 'UNSET'}**",
        f"- SMTP Port: **{cfg.get('port') or 'UNSET'}**",
        f"- Missing Required Vars: **{', '.join(cfg.get('missing') or []) if cfg.get('missing') else 'None'}**",
    ]
    _write(REPORT_DIR / "email_configuration_report.md", "\n".join(cfg_report))

    validation_rows = [
        ["Provider", conn.get("provider")],
        ["Configuration", "PASS" if conn.get("configuration_ok") else "FAIL"],
        ["DNS", "PASS" if conn.get("dns_ok") else "FAIL"],
        ["TLS", "PASS" if conn.get("tls_ok") else "FAIL"],
        ["Authentication", "PASS" if conn.get("auth_ok") else "FAIL"],
        ["Connection", "PASS" if conn.get("connect_ok") else "FAIL"],
        ["Delivery Capability", "PASS" if conn.get("delivery_capable") else "FAIL"],
        ["Error", conn.get("error") or "None"],
    ]
    validation_report = [
        "# Email Validation Report",
        "",
        f"- Generated At (UTC): **{now}**",
        "",
        _md_table(["Check", "Result"], validation_rows),
    ]
    _write(REPORT_DIR / "email_validation_report.md", "\n".join(validation_report))

    delivery_report = [
        "# Test Delivery Report",
        "",
        f"- Generated At (UTC): **{now}**",
        f"- Provider: **{provider}**",
        f"- Recipient: **{', '.join(send_result.recipients) if send_result.recipients else 'UNSET'}**",
        f"- Subject: **{subject}**",
        f"- Delivery Status: **{send_result.status}**",
        f"- Message: **{send_result.message}**",
        f"- Provider Response: **{send_result.provider_response}**",
        f"- Retries Used: **{send_result.retry_count}**",
        "",
        "## Remaining Blockers",
    ]
    if send_result.status != "DELIVERY_ACCEPTED":
        delivery_report.append(f"- {send_result.message}")
    else:
        delivery_report.append("- None detected at SMTP acceptance stage.")

    _write(REPORT_DIR / "test_delivery_report.md", "\n".join(delivery_report))

    summary = {
        "provider": provider,
        "configuration_status": "CONFIGURED" if cfg.get("configured") else "MISSING_CONFIGURATION",
        "connection_status": "PASS" if conn.get("delivery_capable") else "FAIL",
        "delivery_status": send_result.status,
        "provider_response": send_result.provider_response,
        "reports": [
            "reports/email/email_configuration_report.md",
            "reports/email/email_validation_report.md",
            "reports/email/test_delivery_report.md",
        ],
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
