from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.system_health_service import generate_and_send_daily_system_health_report


def main() -> int:
    result = generate_and_send_daily_system_health_report()
    print(result)
    return 0 if result.get("delivery_confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())