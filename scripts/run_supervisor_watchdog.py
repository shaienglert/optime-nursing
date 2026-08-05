from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.chief_ai_supervisor import run_independent_supervisor_watchdog


def main() -> int:
    max_lateness = 180
    if len(sys.argv) > 1:
        try:
            max_lateness = int(sys.argv[1])
        except ValueError:
            max_lateness = 180

    db = SessionLocal()
    try:
        result = run_independent_supervisor_watchdog(db, max_allowed_lateness_seconds=max_lateness)
    finally:
        db.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not bool(result.get("detected_missed_cycle")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
