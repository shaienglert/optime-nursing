"""Authenticated, bounded daily production research and coverage verification."""
import json
import os
from pathlib import Path
import sys
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

    queued = call("/admin/research-institute/refresh", "POST")
    batches = []
    for _ in range(20):
        batch = call("/admin/research-institute/process?limit=10", "POST")
        batches.append(batch)
        if batch.get("processed") == 0 or batch.get("remaining") == 0:
            break
    coverage = call("/admin/research-institute/coverage")
    Path("research-institute-coverage.json").write_text(json.dumps({"queued": queued, "batches": batches, "coverage": coverage}, indent=2), encoding="utf-8")
    print(json.dumps({"status": coverage["status"], "real_facilities": coverage["real_facilities"], "status_counts": coverage["status_counts"]}))
    # A synthetic-only market must not falsely certify production research.
    return 0 if coverage["status"] == "CURRENT" and coverage["real_facilities"] > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
