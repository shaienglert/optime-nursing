from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.daily_system_health_service import REPORT_JSON_PATH, REPORT_MD_PATH, generate_daily_system_health


def main() -> int:
    db = SessionLocal()
    try:
        payload = generate_daily_system_health(db)
    finally:
        db.close()
    print(
        json.dumps(
            {
                "report_md": str(REPORT_MD_PATH),
                "report_json": str(REPORT_JSON_PATH),
                "overall_platform_status": payload.get("overall_platform_status"),
                "email_delivery": payload.get("email_delivery"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())