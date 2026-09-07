from __future__ import annotations

"""Run a degraded search again once the model is back, and send the family the real report.

A family who searched during an outage got a set of communities that met their stated
requirements and an honest note that nobody had compared them. This closes that loop: they
leave an address, and when the comparison is possible the search runs again -- their
questionnaire, their words, their market -- and the report goes out.

Two rules keep the promise honest.

A retry that degrades again is not a delivery. The row stays pending and nothing is sent,
because a second unranked set is not what was asked for and sending it would spend the one
piece of attention this family agreed to give us.

The address is used once, for this. It is not a subscription, and the row carries no
consent to anything else.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.deferred_report import DeferredDecisionReport, DeferredReportStatus

# A search is only worth re-running while the family could still act on it. Past this the
# row is abandoned rather than retried forever against a decision that has been made.
MAX_AGE_DAYS = 14
MAX_ATTEMPTS = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_email(value: str) -> bool:
    text = str(value or "").strip()
    if len(text) < 6 or len(text) > 254 or " " in text:
        return False
    local, _, domain = text.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def request_deferred_report(
    db: Session,
    *,
    email: str,
    questionnaire: Dict[str, Any],
    query_text: str,
    market: Optional[str] = None,
    limit: int = 5,
    degraded_reason: Optional[str] = None,
    eligible_at_request: Optional[int] = None,
) -> Dict[str, Any]:
    address = str(email or "").strip()
    if not _valid_email(address):
        raise ValueError("A deliverable email address is required.")
    if not str(query_text or "").strip():
        raise ValueError("The original search text is required to reproduce the report.")

    # One pending row per address and search. A family pressing the button twice is asking
    # once; a second row would mean two identical emails.
    existing = (
        db.query(DeferredDecisionReport)
        .filter(
            DeferredDecisionReport.email == address,
            DeferredDecisionReport.query_text == query_text,
            DeferredDecisionReport.status == DeferredReportStatus.PENDING,
        )
        .one_or_none()
    )
    if existing is not None:
        return {"request_id": existing.id, "status": existing.status.value, "created": False}

    row = DeferredDecisionReport(
        email=address,
        questionnaire_json=json.dumps(questionnaire or {}, ensure_ascii=False),
        query_text=str(query_text),
        market=(market or os.getenv("OPTIME_CANONICAL_MARKET") or None),
        result_limit=max(1, min(int(limit or 5), 25)),
        degraded_reason=degraded_reason,
        eligible_at_request=eligible_at_request,
        status=DeferredReportStatus.PENDING,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"request_id": row.id, "status": row.status.value, "created": True}


def _render_report(row: DeferredDecisionReport, result: Dict[str, Any]) -> tuple[str, str]:
    rows = result.get("results") or []
    lines = [
        "The comparison you asked for is ready.",
        "",
        "When you searched, the part of our system that compares communities against your",
        "situation was unavailable, so we showed you a list in no particular order. It has",
        "run now, and this is the result.",
        "",
        f"Your search: {row.query_text}",
        "",
        f"{len(rows)} communities, best fit first:",
        "",
    ]
    for index, item in enumerate(rows, start=1):
        name = str(item.get("facility_name") or item.get("name") or "Unnamed community")
        city = str(item.get("city") or "")
        fit = item.get("care_setting_fit") if isinstance(item.get("care_setting_fit"), dict) else {}
        status = str(fit.get("status") or "")
        lines.append(f"{index}. {name}{f' — {city}' if city else ''}{f'  [{status}]' if status else ''}")

    lines += [
        "",
        "This report was produced because you asked to be told when the full comparison",
        "was possible. Your address was used for this message and nothing else.",
        "",
        "OPTIME",
    ]
    subject = f"Your senior living comparison is ready ({len(rows)} communities)"
    return subject, "\n".join(lines)


def process_pending_reports(db: Session, limit: int = 25) -> Dict[str, Any]:
    """Retry pending requests; send only the ones that came back genuinely ranked."""
    # Imported here: the engine pulls in a large graph, and capturing a request must not
    # depend on the whole decision runtime being importable.
    from app.services.email_service import send_email_detailed  # noqa: PLC0415
    from app.services.patient_decision_engine import run_patient_decision_engine  # noqa: PLC0415

    cutoff = _now() - timedelta(days=MAX_AGE_DAYS)
    pending: List[DeferredDecisionReport] = (
        db.query(DeferredDecisionReport)
        .filter(DeferredDecisionReport.status == DeferredReportStatus.PENDING)
        .order_by(DeferredDecisionReport.requested_at)
        .limit(max(1, min(int(limit), 200)))
        .all()
    )

    sent = still_degraded = abandoned = failed = 0

    for row in pending:
        requested = row.requested_at
        if requested is not None and requested.tzinfo is None:
            requested = requested.replace(tzinfo=timezone.utc)
        if (requested is not None and requested < cutoff) or row.attempts >= MAX_ATTEMPTS:
            row.status = DeferredReportStatus.ABANDONED
            row.last_error = "Expired before the ranking model became available."
            abandoned += 1
            continue

        row.attempts = (row.attempts or 0) + 1
        row.last_attempt_at = _now()

        try:
            questionnaire = json.loads(row.questionnaire_json or "{}")
        except json.JSONDecodeError:
            row.status = DeferredReportStatus.FAILED
            row.last_error = "Stored questionnaire could not be read."
            failed += 1
            continue

        previous_market = os.environ.get("OPTIME_CANONICAL_MARKET")
        if row.market:
            os.environ["OPTIME_CANONICAL_MARKET"] = row.market
        try:
            result = run_patient_decision_engine(questionnaire, row.query_text, limit=row.result_limit)
        except Exception as error:  # noqa: BLE001 -- a failed retry is a retry, not a lost request
            row.last_error = f"{type(error).__name__}: {error}"
            failed += 1
            continue
        finally:
            if row.market:
                if previous_market is None:
                    os.environ.pop("OPTIME_CANONICAL_MARKET", None)
                else:
                    os.environ["OPTIME_CANONICAL_MARKET"] = previous_market

        decision = result.get("decision_intelligence") or {}
        canonical = decision.get("canonical_decision_state") or {}
        rows_out = result.get("results") or []

        # The whole promise was a studied comparison. A second unranked set is not that,
        # so the row waits rather than spending the family's attention on the same answer.
        if canonical.get("is_degraded_result") or not rows_out:
            row.last_error = "Ranking still unavailable; left pending."
            still_degraded += 1
            continue

        subject, body = _render_report(row, result)
        outcome = send_email_detailed(subject=subject, body_text=body, recipients=[row.email])
        if getattr(outcome, "success", False):
            row.status = DeferredReportStatus.SENT
            row.delivered_at = _now()
            row.last_error = None
            sent += 1
        else:
            row.last_error = str(getattr(outcome, "error", "Email delivery failed."))
            failed += 1

    db.commit()
    return {
        "examined": len(pending),
        "sent": sent,
        "still_degraded": still_degraded,
        "failed": failed,
        "abandoned": abandoned,
    }


def pending_report_summary(db: Session) -> Dict[str, Any]:
    counts = {status.value: 0 for status in DeferredReportStatus}
    for row in db.query(DeferredDecisionReport).all():
        counts[row.status.value] = counts.get(row.status.value, 0) + 1
    return {"counts": counts, "max_age_days": MAX_AGE_DAYS, "max_attempts": MAX_ATTEMPTS}


__all__ = [
    "request_deferred_report",
    "process_pending_reports",
    "pending_report_summary",
    "MAX_AGE_DAYS",
    "MAX_ATTEMPTS",
]
