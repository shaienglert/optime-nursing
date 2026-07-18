import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Tuple


DEFAULT_RECIPIENT = "office@optime-nursing.com"


def configured_recipients() -> List[str]:
    primary = os.getenv("OPTIME_EXEC_REPORT_RECIPIENT", DEFAULT_RECIPIENT).strip() or DEFAULT_RECIPIENT
    extra_raw = os.getenv("OPTIME_EXEC_REPORT_ADDITIONAL_RECIPIENTS", "")
    extras = [part.strip() for part in extra_raw.split(",") if part.strip()]

    seen = set()
    out: List[str] = []
    for email in [primary, *extras]:
        low = email.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(email)
    return out


def send_email(
    *,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    recipients: Optional[List[str]] = None,
) -> Tuple[bool, str, List[str]]:
    host = os.getenv("OPTIME_SMTP_HOST", "").strip()
    port = int(os.getenv("OPTIME_SMTP_PORT", "587").strip())
    username = os.getenv("OPTIME_SMTP_USERNAME", "").strip()
    password = os.getenv("OPTIME_SMTP_PASSWORD", "")
    sender = os.getenv("OPTIME_SMTP_FROM", "optime@localhost").strip()
    use_tls = os.getenv("OPTIME_SMTP_USE_TLS", "1").strip() != "0"

    final_recipients = recipients or configured_recipients()
    if not final_recipients:
        return False, "No recipients configured", []

    if not host:
        return False, "SMTP host is not configured (OPTIME_SMTP_HOST)", final_recipients

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(final_recipients)
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(host=host, port=port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(msg)
        return True, "sent", final_recipients
    except Exception as exc:  # pragma: no cover - operational path
        return False, f"SMTP send failed: {exc}", final_recipients
