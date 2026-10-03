"""Authenticated, bounded daily production research and coverage verification."""
import json
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import re
from urllib.parse import urlparse
import requests


def main():
    base = os.environ.get("OOMNIK_RESEARCH_BACKEND_URL", "").strip().rstrip("/")
    token = os.environ.get("OOMNIK_RESEARCH_ADMIN_TOKEN", "").strip()
    if urlparse(base).scheme != "https" or not token:
        raise SystemExit("Research monitoring requires a configured HTTPS backend and admin credential.")
    headers = {"X-Admin-Token": token}

    def call(path, method="GET", authenticated=True):
        response = requests.request(method, base + path, headers=headers if authenticated else {}, timeout=(5, 120), allow_redirects=False)
        if not 200 <= response.status_code < 300:
            # Do not print request headers or credentials, including on HTTP failure.
            raise RuntimeError(f"Research endpoint failed with HTTP {response.status_code}")
        return response.json()

    try:
        queued = call("/admin/research-institute/refresh", "POST")
        batches = []
        for _ in range(20):
            batch = call("/admin/research-institute/process?limit=10", "POST")
            batches.append(batch)
            if batch.get("processed") == 0 or batch.get("remaining") == 0:
                break
        coverage = call("/admin/research-institute/coverage")
    finally:
        # Audit the last complete UTC day even if refresh fails. An outage is not
        # permission to silently omit the report. A failed audit remains a failure.
        day = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        daily = call(f"/admin/research-institute/daily-reports?report_date={day}", "POST")
        if daily.get("report_date") != day:
            raise RuntimeError("Unexpected daily report date")
        destination = Path("research-daily-reports") / day
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "summary.json").write_text(json.dumps(daily, ensure_ascii=False, indent=2), encoding="utf-8")
        for agent in daily["agents"]:
            # Agent keys originate in DB registries; never use them as arbitrary paths.
            key = str(agent["agent_key"])
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", key):
                raise RuntimeError("Invalid agent key in report export")
            (destination / f"{key}.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("research-institute-coverage.json").write_text(json.dumps({"queued": queued, "batches": batches, "coverage": coverage}, indent=2), encoding="utf-8")
    print(json.dumps({"status": coverage["status"], "real_facilities": coverage["real_facilities"], "status_counts": coverage["status_counts"]}))
    # A synthetic-only market must not falsely certify production research.
    return 0 if coverage["status"] == "CURRENT" and coverage["real_facilities"] > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
