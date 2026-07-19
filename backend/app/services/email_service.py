import os
import json
import smtplib
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_RECIPIENT = "office@optime-nursing.com"
STARTUP_TEST_SUBJECT = "OPTIME Email System Test"
STARTUP_TEST_BODY = "OPTIME automated email delivery is operational."


@dataclass
class EmailSendResult:
    ok: bool
    status: str
    message: str
    provider: str
    recipients: List[str]
    attempted_at_utc: str
    retry_count: int
    provider_response: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _email_reports_dir() -> Path:
    p = _repo_root() / "reports" / "email"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _delivery_log_path() -> Path:
    return _email_reports_dir() / "delivery_log.jsonl"


def _startup_test_state_path() -> Path:
    return _email_reports_dir() / "startup_test_state.json"


def _append_delivery_log(entry: Dict[str, object]) -> None:
    path = _delivery_log_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(__import__("json").dumps(entry, ensure_ascii=True) + "\n")


def _deployment_key() -> str:
    return (
        os.getenv("RENDER_GIT_COMMIT", "").strip()
        or os.getenv("RENDER_DEPLOY_ID", "").strip()
        or os.getenv("OPTIME_SMTP_STARTUP_TEST_KEY", "").strip()
        or "default"
    )


def _load_startup_test_state() -> Dict[str, object]:
    path = _startup_test_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_startup_test_state(state: Dict[str, object]) -> None:
    path = _startup_test_state_path()
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def provider_name() -> str:
    # Existing implementation is SMTP-only. Keep single provider to avoid split delivery systems.
    return "SMTP"


def validate_email_configuration() -> Dict[str, object]:
    host = os.getenv("OPTIME_SMTP_HOST", "").strip()
    port = os.getenv("OPTIME_SMTP_PORT", "587").strip()
    sender = os.getenv("OPTIME_SMTP_FROM", "").strip()
    recipients = configured_recipients()

    missing: List[str] = []
    if not host:
        missing.append("OPTIME_SMTP_HOST")
    if not sender:
        missing.append("OPTIME_SMTP_FROM")
    if not recipients:
        missing.append("OPTIME_EXEC_REPORT_RECIPIENT")

    # Username/password can be optional for local relays, so do not hard-fail here.
    return {
        "provider": provider_name(),
        "host": host,
        "port": port,
        "sender": sender,
        "recipients": recipients,
        "configured": len(missing) == 0,
        "missing": missing,
    }


def test_smtp_connection() -> Dict[str, object]:
    cfg = validate_email_configuration()
    host = str(cfg.get("host") or "")
    port = int(str(cfg.get("port") or "587"))
    username = os.getenv("OPTIME_SMTP_USERNAME", "").strip()
    password = os.getenv("OPTIME_SMTP_PASSWORD", "")
    use_tls = os.getenv("OPTIME_SMTP_USE_TLS", "1").strip() != "0"

    result = {
        "provider": provider_name(),
        "configuration_ok": bool(cfg.get("configured")),
        "missing": cfg.get("missing") or [],
        "dns_ok": False,
        "tls_ok": False,
        "auth_ok": False,
        "connect_ok": False,
        "delivery_capable": False,
        "error": None,
    }

    if not cfg.get("configured"):
        result["error"] = "Missing required SMTP configuration"
        return result

    try:
        socket.getaddrinfo(host, port)
        result["dns_ok"] = True
    except Exception as exc:  # pragma: no cover - operational path
        result["error"] = f"DNS resolution failed: {exc}"
        return result

    try:
        with smtplib.SMTP(host=host, port=port, timeout=30) as server:
            server.ehlo()
            result["connect_ok"] = True
            if use_tls:
                ctx = ssl.create_default_context()
                server.starttls(context=ctx)
                server.ehlo()
                result["tls_ok"] = True
            else:
                result["tls_ok"] = True

            if username:
                server.login(username, password)
                result["auth_ok"] = True
            else:
                # If no username is configured, treat as relay/no-auth mode.
                result["auth_ok"] = True

            result["delivery_capable"] = True
    except Exception as exc:  # pragma: no cover - operational path
        result["error"] = f"SMTP connection/auth test failed: {exc}"

    return result


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


def send_email_detailed(
    *,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    max_retries: Optional[int] = None,
) -> EmailSendResult:
    host = os.getenv("OPTIME_SMTP_HOST", "").strip()
    port = int(os.getenv("OPTIME_SMTP_PORT", "587").strip())
    username = os.getenv("OPTIME_SMTP_USERNAME", "").strip()
    password = os.getenv("OPTIME_SMTP_PASSWORD", "")
    sender = os.getenv("OPTIME_SMTP_FROM", "optime@localhost").strip()
    use_tls = os.getenv("OPTIME_SMTP_USE_TLS", "1").strip() != "0"
    retries = max_retries if max_retries is not None else int(os.getenv("OPTIME_SMTP_MAX_RETRIES", "2"))
    attempted_at = datetime.now(timezone.utc).isoformat()

    final_recipients = recipients or configured_recipients()
    if not final_recipients:
        res = EmailSendResult(
            ok=False,
            status="DELIVERY_BLOCKED",
            message="No recipients configured",
            provider=provider_name(),
            recipients=[],
            attempted_at_utc=attempted_at,
            retry_count=0,
            provider_response="No recipients configured",
        )
        _append_delivery_log(res.__dict__)
        return res

    if not host:
        res = EmailSendResult(
            ok=False,
            status="DELIVERY_BLOCKED",
            message="SMTP host is not configured (OPTIME_SMTP_HOST)",
            provider=provider_name(),
            recipients=final_recipients,
            attempted_at_utc=attempted_at,
            retry_count=0,
            provider_response="Missing OPTIME_SMTP_HOST",
        )
        _append_delivery_log(res.__dict__)
        return res

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(final_recipients)
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    for attachment in attachments or []:
        p = Path(attachment)
        if not p.is_absolute():
            p = _repo_root() / p
        if not p.exists() or not p.is_file():
            continue
        data = p.read_bytes()
        maintype = "application"
        subtype = "octet-stream"
        if p.suffix.lower() in {".md", ".txt", ".log"}:
            maintype = "text"
            subtype = "plain"
        elif p.suffix.lower() == ".html":
            maintype = "text"
            subtype = "html"
        elif p.suffix.lower() == ".json":
            maintype = "application"
            subtype = "json"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)

    last_error = ""
    for attempt in range(retries + 1):
        try:
            with smtplib.SMTP(host=host, port=port, timeout=30) as server:
                server.ehlo()
                if use_tls:
                    ctx = ssl.create_default_context()
                    server.starttls(context=ctx)
                    server.ehlo()
                if username:
                    server.login(username, password)
                send_resp = server.send_message(msg)
            # Empty dict usually means accepted by SMTP server for all recipients.
            provider_response = f"SMTP_ACCEPTED={send_resp == {}}; SEND_RESPONSE={send_resp}"
            res = EmailSendResult(
                ok=True,
                status="DELIVERY_ACCEPTED",
                message="sent",
                provider=provider_name(),
                recipients=final_recipients,
                attempted_at_utc=attempted_at,
                retry_count=attempt,
                provider_response=provider_response,
            )
            _append_delivery_log(res.__dict__)
            return res
        except Exception as exc:  # pragma: no cover - operational path
            last_error = str(exc)

    res = EmailSendResult(
        ok=False,
        status="DELIVERY_FAILED",
        message=f"SMTP send failed after retries: {last_error}",
        provider=provider_name(),
        recipients=final_recipients,
        attempted_at_utc=attempted_at,
        retry_count=retries,
        provider_response=last_error,
    )
    _append_delivery_log(res.__dict__)
    return res


def send_email(
    *,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    recipients: Optional[List[str]] = None,
) -> Tuple[bool, str, List[str]]:
    # Backward-compatible wrapper for existing call sites.
    result = send_email_detailed(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        recipients=recipients,
    )
    return result.ok, result.message, result.recipients


def send_startup_test_email_once() -> Dict[str, object]:
    if os.getenv("OPTIME_SMTP_STARTUP_TEST_ENABLED", "1").strip() == "0":
        return {"attempted": False, "reason": "disabled"}

    deployment_key = _deployment_key()
    state = _load_startup_test_state()
    if state.get("deployment_key") == deployment_key and bool(state.get("attempted")):
        return {"attempted": False, "reason": "already_attempted_for_deployment"}

    result = send_email_detailed(
        subject=STARTUP_TEST_SUBJECT,
        body_text=STARTUP_TEST_BODY,
        recipients=[DEFAULT_RECIPIENT],
        max_retries=0,
    )

    smtp_accepted = result.status == "DELIVERY_ACCEPTED" and "SMTP_ACCEPTED=True" in result.provider_response
    _save_startup_test_state(
        {
            "deployment_key": deployment_key,
            "attempted": True,
            "attempted_at_utc": result.attempted_at_utc,
            "status": result.status,
            "smtp_accepted": smtp_accepted,
            "complete": smtp_accepted,
        }
    )

    error_type = None
    if result.status != "DELIVERY_ACCEPTED":
        if result.status == "DELIVERY_BLOCKED":
            error_type = "CONFIGURATION"
        elif result.status == "DELIVERY_FAILED":
            error_type = "SMTP_SEND_FAILURE"
        else:
            error_type = "UNKNOWN"

    return {
        "attempted": True,
        "status": result.status,
        "smtp_accepted": smtp_accepted,
        "error_type": error_type,
        "error_message": result.message,
    }
