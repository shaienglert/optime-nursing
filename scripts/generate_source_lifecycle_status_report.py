from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.source_lifecycle_service import REGISTRY_PATH, STATUS_REPORT_PATH, load_registry, render_status_report


def main() -> int:
    payload = load_registry(REGISTRY_PATH)
    report = render_status_report(payload)
    STATUS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_REPORT_PATH.write_text(report, encoding="utf-8")
    print(str(STATUS_REPORT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())