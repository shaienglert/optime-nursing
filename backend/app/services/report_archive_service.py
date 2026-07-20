import json
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ReportRecord:
    report_id: str
    report_date: str
    generated_at_utc: str
    subject: str
    markdown_path: str
    html_path: str
    json_path: str
    sent: bool
    sent_at_utc: Optional[str]
    recipients: List[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def daily_reports_dir() -> Path:
    return _repo_root() / "reports" / "daily"


def daily_archive_dir() -> Path:
    return daily_reports_dir() / "archive"


def _index_path() -> Path:
    return daily_reports_dir() / "index.json"


def _send_log_path() -> Path:
    return daily_reports_dir() / "send_log.jsonl"


def ensure_archive_layout() -> None:
    daily_reports_dir().mkdir(parents=True, exist_ok=True)
    daily_archive_dir().mkdir(parents=True, exist_ok=True)


def _relative(path: Path) -> str:
    return str(path.relative_to(_repo_root())).replace("\\", "/")


def _markdown_to_html(markdown_text: str) -> str:
    # Keep transformation deterministic and dependency-free.
    body = escape(markdown_text)
    body = body.replace("\n", "<br/>\n")
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"/>"
        "<title>OPTIME Executive Intelligence Report</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;line-height:1.45;}"
        "h1,h2,h3{margin-top:20px;}"
        "code{background:#f5f5f5;padding:2px 4px;border-radius:4px;}"
        "</style></head><body>"
        f"{body}"
        "</body></html>"
    )


def _load_index() -> List[Dict[str, object]]:
    ensure_archive_layout()
    p = _index_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        return []
    return []


def _save_index(rows: List[Dict[str, object]]) -> None:
    ensure_archive_layout()
    _index_path().write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _canonical_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    best_by_date: Dict[str, Dict[str, object]] = {}
    for row in rows:
        report_date = str(row.get("report_date") or "").strip()
        if not report_date:
            continue
        current = best_by_date.get(report_date)
        if current is None:
            best_by_date[report_date] = row
            continue
        current_generated_at = str(current.get("generated_at_utc") or "")
        next_generated_at = str(row.get("generated_at_utc") or "")
        if next_generated_at >= current_generated_at:
            best_by_date[report_date] = row

    return sorted(best_by_date.values(), key=lambda r: str(r.get("report_date", "")))


def latest_record() -> Optional[Dict[str, object]]:
    rows = _canonical_rows(_load_index())
    if not rows:
        return None
    return rows[-1]


def previous_record() -> Optional[Dict[str, object]]:
    rows = _canonical_rows(_load_index())
    if len(rows) < 2:
        return None
    return rows[-2]


def history(limit: int = 30) -> List[Dict[str, object]]:
    rows = _canonical_rows(_load_index())
    rows_sorted = list(reversed(rows))
    return rows_sorted[: max(1, min(limit, 365))]


def load_report_json(relative_path: str) -> Optional[Dict[str, object]]:
    p = _repo_root() / Path(relative_path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return None
    return None


def create_report_artifacts(subject: str, markdown_text: str, report_json: Dict[str, object]) -> ReportRecord:
    ensure_archive_layout()
    now = datetime.now(timezone.utc)
    report_date = now.strftime("%Y-%m-%d")
    report_id = report_date

    base_name = f"executive_intelligence_report_{report_date}"
    md_path = daily_archive_dir() / f"{base_name}.md"
    html_path = daily_archive_dir() / f"{base_name}.html"
    json_path = daily_archive_dir() / f"{base_name}.json"

    md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
    html_path.write_text(_markdown_to_html(markdown_text), encoding="utf-8")

    payload = dict(report_json)
    payload["report_id"] = report_id
    payload["report_date"] = report_date
    payload["generated_at_utc"] = now.isoformat()
    payload["subject"] = subject
    payload["artifacts"] = {
        "markdown": _relative(md_path),
        "html": _relative(html_path),
        "json": _relative(json_path),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Keep latest pointers in reports/daily for easy access.
    daily_reports_dir().joinpath("latest.md").write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
    daily_reports_dir().joinpath("latest.html").write_text(_markdown_to_html(markdown_text), encoding="utf-8")
    daily_reports_dir().joinpath("latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    record = ReportRecord(
        report_id=report_id,
        report_date=report_date,
        generated_at_utc=now.isoformat(),
        subject=subject,
        markdown_path=_relative(md_path),
        html_path=_relative(html_path),
        json_path=_relative(json_path),
        sent=False,
        sent_at_utc=None,
        recipients=[],
    )

    rows = _load_index()
    rows = [row for row in rows if str(row.get("report_date") or "") != report_date]
    rows.append(record.__dict__)
    _save_index(rows)
    return record


def mark_report_sent(report_id: str, recipients: List[str]) -> None:
    rows = _load_index()
    sent_at = datetime.now(timezone.utc).isoformat()
    for row in rows:
        if str(row.get("report_id")) == report_id:
            row["sent"] = True
            row["sent_at_utc"] = sent_at
            row["recipients"] = recipients
            break
    _save_index(rows)

    ensure_archive_layout()
    _send_log_path().write_text("", encoding="utf-8") if not _send_log_path().exists() else None
    with _send_log_path().open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "report_id": report_id,
                    "sent_at_utc": sent_at,
                    "recipients": recipients,
                }
            )
            + "\n"
        )
